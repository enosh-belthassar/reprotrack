"""Projects and membership API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.core.permissions import ensure_project_access
from backend.app.db.session import get_db
from backend.app.models.issue import Issue
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)
from backend.app.services.project_service import (
    add_project_member,
    create_project,
    list_accessible_projects,
    list_project_members,
    remove_project_member,
    update_project,
    update_project_member_role,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_accessible_projects(db, current_user)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def post_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proj = create_project(db, current_user, data)
    return ProjectResponse(
        id=proj.id,
        key=proj.key,
        name=proj.name,
        description=proj.description,
        is_active=proj.is_active,
        created_at=proj.created_at,
        issue_count=0,
        my_role="PROJECT_ADMIN",
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_detail(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = ensure_project_access(db, project_id, current_user)
    proj = db.get(Project, project_id)
    issue_count = (
        db.execute(select(func.count(Issue.id)).where(Issue.project_id == proj.id)).scalar() or 0
    )
    return ProjectResponse(
        id=proj.id,
        key=proj.key,
        name=proj.name,
        description=proj.description,
        is_active=proj.is_active,
        created_at=proj.created_at,
        issue_count=issue_count,
        my_role="GLOBAL_ADMIN"
        if current_user.global_role == "GLOBAL_ADMIN"
        else (member.role if member else None),
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proj = update_project(db, current_user, project_id, data)
    issue_count = (
        db.execute(select(func.count(Issue.id)).where(Issue.project_id == proj.id)).scalar() or 0
    )
    return ProjectResponse(
        id=proj.id,
        key=proj.key,
        name=proj.name,
        description=proj.description,
        is_active=proj.is_active,
        created_at=proj.created_at,
        issue_count=issue_count,
    )


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def get_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_project_members(db, current_user, project_id)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_member(
    project_id: int,
    data: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return add_project_member(db, current_user, project_id, data)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def patch_member_role(
    project_id: int,
    user_id: int,
    data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_project_member_role(db, current_user, project_id, user_id, data.role)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    remove_project_member(db, current_user, project_id, user_id)
