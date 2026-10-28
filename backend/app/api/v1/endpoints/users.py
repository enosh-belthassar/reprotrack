"""User administration and audit log API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_admin
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserResponse, UserUpdate
from backend.app.services.user_service import (
    create_user,
    deactivate_user,
    list_audit_events,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


class AuditEventResponse(BaseModel):
    id: int
    actor_id: int | None
    actor_name: str
    action: str
    entity_type: str
    entity_id: str | None
    metadata_json: str | None
    timestamp: datetime
    request_id: str | None


def serialize_user(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        display_name=u.display_name,
        email_normalized=u.email_normalized,
        global_role=u.global_role,
        is_active=u.is_active,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


@router.get("", response_model=list[UserResponse])
def get_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = list_users(db, admin)
    return [serialize_user(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def post_user(
    data: UserCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = create_user(db, admin, data)
    return serialize_user(user)


@router.patch("/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    data: UserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = update_user(db, admin, user_id, data)
    return serialize_user(user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def post_deactivate_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = deactivate_user(db, admin, user_id)
    return serialize_user(user)


@router.get("/audit-log", response_model=list[AuditEventResponse])
def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return list_audit_events(db, admin, limit=limit)
