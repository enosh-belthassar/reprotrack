"""Role definitions and backend-enforced authorization policies."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    ForbiddenException,
    ProjectAccessDeniedException,
    ProjectNotFoundException,
    VerificationNotAllowedException,
)
from backend.app.models.issue import Issue
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User


class GlobalRole:
    GLOBAL_ADMIN = "GLOBAL_ADMIN"
    USER = "USER"


class ProjectRole:
    PROJECT_ADMIN = "PROJECT_ADMIN"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    REPORTER = "REPORTER"
    VIEWER = "VIEWER"


ALL_PROJECT_ROLES: set[str] = {
    ProjectRole.PROJECT_ADMIN,
    ProjectRole.DEVELOPER,
    ProjectRole.TESTER,
    ProjectRole.REPORTER,
    ProjectRole.VIEWER,
}

# Roles that can create/report issues
ISSUE_CREATOR_ROLES: set[str] = {
    ProjectRole.PROJECT_ADMIN,
    ProjectRole.DEVELOPER,
    ProjectRole.TESTER,
    ProjectRole.REPORTER,
}

# Roles that can triage/change severity/priority
TRIAGE_ROLES: set[str] = {
    ProjectRole.PROJECT_ADMIN,
    ProjectRole.TESTER,
    ProjectRole.DEVELOPER,
}

# Roles that can verify fixes
VERIFICATION_ROLES: set[str] = {
    ProjectRole.PROJECT_ADMIN,
    ProjectRole.TESTER,
}

# Roles that can add investigation comments (read-only VIEWER excluded)
COMMENT_CREATOR_ROLES: set[str] = {
    ProjectRole.PROJECT_ADMIN,
    ProjectRole.DEVELOPER,
    ProjectRole.TESTER,
    ProjectRole.REPORTER,
}


def is_global_admin(user: User) -> bool:
    return user.is_active and user.global_role == GlobalRole.GLOBAL_ADMIN


def require_global_admin(user: User) -> None:
    if not is_global_admin(user):
        raise ForbiddenException("Administrator privileges required.")


def get_project_member(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def ensure_project_access(db: Session, project_id: int, user: User) -> ProjectMember | None:
    """Ensure user has access to project. Global admins have access. Others must be members."""
    # Check if project exists first
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise ProjectNotFoundException()

    if is_global_admin(user):
        # Global admin has access, may not have membership record
        member = get_project_member(db, project_id, user.id)
        return member

    member = get_project_member(db, project_id, user.id)
    if not member:
        raise ProjectAccessDeniedException("You are not a member of this project.")
    return member


def require_project_role(
    db: Session,
    project_id: int,
    user: User,
    allowed_roles: set[str],
) -> ProjectMember | None:
    """Verify that user is Global Admin or has one of the allowed roles in the project."""
    member = ensure_project_access(db, project_id, user)
    if is_global_admin(user):
        return member

    if not member or member.role not in allowed_roles:
        raise ForbiddenException("You do not have the required role in this project.")
    return member


def validate_fix_verification_tester(
    tester: User, issue: Issue, allow_self_verification: bool = False
) -> None:
    """Enforce separation of duties: Developer cannot verify their own fix by default."""
    if is_global_admin(tester):
        return

    if not allow_self_verification:
        if issue.assignee_id and issue.assignee_id == tester.id:
            raise VerificationNotAllowedException(
                "Separation of duties violation: Assignee/developer cannot verify their own fix."
            )
        if hasattr(issue, "events") and issue.events:
            for ev in issue.events:
                if (
                    ev.event_type == "STATUS_CHANGED"
                    and ev.new_value == "FIXED"
                    and ev.actor_id == tester.id
                ):
                    raise VerificationNotAllowedException(
                        "Separation of duties violation: Developer who fixed this issue cannot verify their own fix."
                    )
