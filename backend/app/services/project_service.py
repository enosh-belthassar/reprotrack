"""Project and project membership management services."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    DuplicateProjectKeyException,
    ForbiddenException,
    ProjectNotFoundException,
    ValidationErrorException,
)
from backend.app.core.permissions import (
    ProjectRole,
    ensure_project_access,
    is_global_admin,
    require_project_role,
)
from backend.app.core.request_context import get_request_id
from backend.app.models.audit import AuditEvent
from backend.app.models.issue import Issue
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User
from backend.app.schemas.project import ProjectCreate, ProjectMemberCreate, ProjectUpdate


def list_accessible_projects(db: Session, user: User) -> list[dict]:
    if is_global_admin(user):
        stmt = (
            select(Project).where(Project.is_active.is_(True)).order_by(Project.created_at.desc())
        )
        projects = db.execute(stmt).scalars().all()
        role_map = {}
    else:
        stmt = (
            select(Project, ProjectMember.role)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user.id, Project.is_active.is_(True))
            .order_by(Project.created_at.desc())
        )
        results = db.execute(stmt).all()
        projects = [r[0] for r in results]
        role_map = {r[0].id: r[1] for r in results}

    output = []
    for proj in projects:
        issue_count = (
            db.execute(select(func.count(Issue.id)).where(Issue.project_id == proj.id)).scalar()
            or 0
        )

        my_role = "GLOBAL_ADMIN" if is_global_admin(user) else role_map.get(proj.id)
        output.append(
            {
                "id": proj.id,
                "key": proj.key,
                "name": proj.name,
                "description": proj.description,
                "is_active": proj.is_active,
                "created_at": proj.created_at,
                "issue_count": issue_count,
                "my_role": my_role,
            }
        )
    return output


def create_project(db: Session, user: User, data: ProjectCreate) -> Project:
    key_clean = data.key.strip().upper()
    existing = db.execute(select(Project).where(Project.key == key_clean)).scalar_one_or_none()
    if existing:
        raise DuplicateProjectKeyException(f"Project key '{key_clean}' is already in use.")

    project = Project(
        key=key_clean,
        name=data.name.strip(),
        description=data.description.strip() if data.description else "",
        is_active=True,
        created_by_id=user.id,
        next_issue_number=1,
    )
    db.add(project)
    db.flush()

    # Add creator as PROJECT_ADMIN
    membership = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.PROJECT_ADMIN,
    )
    db.add(membership)

    audit = AuditEvent(
        actor_id=user.id,
        action="PROJECT_CREATED",
        entity_type="project",
        entity_id=str(project.id),
        metadata_json=f'{{"key": "{project.key}", "name": "{project.name}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, user: User, project_id: int, data: ProjectUpdate) -> Project:
    require_project_role(db, project_id, user, {ProjectRole.PROJECT_ADMIN})
    project = db.get(Project, project_id)
    if not project:
        raise ProjectNotFoundException()

    if data.name is not None:
        project.name = data.name.strip()
    if data.description is not None:
        project.description = data.description.strip()
    if data.is_active is not None:
        project.is_active = data.is_active

    audit = AuditEvent(
        actor_id=user.id,
        action="PROJECT_UPDATED",
        entity_type="project",
        entity_id=str(project.id),
        metadata_json=f'{{"name": "{project.name}", "is_active": {project.is_active}}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return project


def list_project_members(db: Session, user: User, project_id: int) -> list[dict]:
    ensure_project_access(db, project_id, user)
    stmt = (
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": member.id,
            "project_id": member.project_id,
            "user_id": u.id,
            "user_name": u.display_name,
            "user_email": u.email_normalized,
            "role": member.role,
            "created_at": member.created_at,
        }
        for member, u in rows
    ]


def add_project_member(db: Session, user: User, project_id: int, data: ProjectMemberCreate) -> dict:
    require_project_role(db, project_id, user, {ProjectRole.PROJECT_ADMIN})
    target_user = db.get(User, data.user_id)
    if not target_user or not target_user.is_active:
        raise ValidationErrorException("Target user not found or inactive.")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValidationErrorException("User is already a member of this project.")

    member = ProjectMember(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role,
    )
    db.add(member)

    audit = AuditEvent(
        actor_id=user.id,
        action="PROJECT_MEMBER_ADDED",
        entity_type="project_member",
        entity_id=str(project_id),
        metadata_json=f'{{"user_id": {data.user_id}, "role": "{data.role}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": target_user.id,
        "user_name": target_user.display_name,
        "user_email": target_user.email_normalized,
        "role": member.role,
        "created_at": member.created_at,
    }


def remove_project_member(db: Session, user: User, project_id: int, target_user_id: int) -> None:
    require_project_role(db, project_id, user, {ProjectRole.PROJECT_ADMIN})
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
    ).scalar_one_or_none()
    if not member:
        raise ValidationErrorException("Membership record not found.")

    if member.role == ProjectRole.PROJECT_ADMIN:
        admin_count = (
            db.execute(
                select(func.count(ProjectMember.id)).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.role == ProjectRole.PROJECT_ADMIN,
                )
            ).scalar()
            or 0
        )
        if admin_count <= 1:
            raise ForbiddenException(
                "Cannot remove the last Project Administrator from the project."
            )

    db.delete(member)
    audit = AuditEvent(
        actor_id=user.id,
        action="PROJECT_MEMBER_REMOVED",
        entity_type="project_member",
        entity_id=str(project_id),
        metadata_json=f'{{"removed_user_id": {target_user_id}}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()


def update_project_member_role(
    db: Session, user: User, project_id: int, target_user_id: int, new_role: str
) -> dict:
    require_project_role(db, project_id, user, {ProjectRole.PROJECT_ADMIN})
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user_id,
        )
    ).scalar_one_or_none()
    if not member:
        raise ValidationErrorException("Membership record not found.")

    target_user = db.get(User, target_user_id)
    if not target_user:
        raise ValidationErrorException("User not found.")

    if member.role == ProjectRole.PROJECT_ADMIN and new_role != ProjectRole.PROJECT_ADMIN:
        admin_count = (
            db.execute(
                select(func.count(ProjectMember.id)).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.role == ProjectRole.PROJECT_ADMIN,
                )
            ).scalar()
            or 0
        )
        if admin_count <= 1:
            raise ForbiddenException(
                "Cannot demote the last Project Administrator from the project."
            )

    old_role = member.role
    member.role = new_role
    audit = AuditEvent(
        actor_id=user.id,
        action="PROJECT_MEMBER_ROLE_UPDATED",
        entity_type="project_member",
        entity_id=str(project_id),
        metadata_json=f'{{"user_id": {target_user_id}, "old_role": "{old_role}", "new_role": "{new_role}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": target_user.id,
        "user_name": target_user.display_name,
        "user_email": target_user.email_normalized,
        "role": member.role,
        "created_at": member.created_at,
    }
