"""Declarative base and model registry."""

from sqlalchemy.orm import DeclarativeBase

from backend.app.core.db_utils import utc_now


class Base(DeclarativeBase):
    pass


# Import all models here so that Base.metadata has all entities registered
# when imported by Alembic, database session scripts, or test runners.
from backend.app.models.audit import AuditEvent  # noqa: E402, F401
from backend.app.models.issue import (  # noqa: E402, F401
    Issue,
    IssueComment,
    IssueEvent,
    VerificationRun,
)
from backend.app.models.project import Project, ProjectMember  # noqa: E402, F401
from backend.app.models.user import LoginAttempt, SessionModel, User  # noqa: E402, F401

__all__ = [
    "AuditEvent",
    "Base",
    "Issue",
    "IssueComment",
    "IssueEvent",
    "LoginAttempt",
    "Project",
    "ProjectMember",
    "SessionModel",
    "User",
    "VerificationRun",
    "utc_now",
]
