"""FastAPI route dependencies for database session and authentication."""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from backend.app.core.exceptions import ForbiddenException, UnauthorizedException
from backend.app.core.permissions import is_global_admin
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.services.auth_service import get_user_by_token


def extract_bearer_token(authorization: str | None = Header(None)) -> str:
    if not authorization:
        raise UnauthorizedException("Authorization header is missing.")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Invalid Authorization format. Expected 'Bearer <token>'.")
    return parts[1].strip()


def get_current_user(
    token: str = Depends(extract_bearer_token),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: Validate opaque token, enforce expiry, revocation, and active user status."""
    return get_user_by_token(db, token)


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: Enforce Global Administrator privilege."""
    if not is_global_admin(current_user):
        raise ForbiddenException("Administrator privileges required.")
    return current_user
