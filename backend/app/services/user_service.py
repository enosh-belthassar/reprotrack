"""User administration and security audit services."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.core.db_utils import utc_now
from backend.app.core.exceptions import (
    LastAdminProtectionException,
    ValidationErrorException,
)
from backend.app.core.permissions import GlobalRole, require_global_admin
from backend.app.core.request_context import get_request_id
from backend.app.core.security import hash_password
from backend.app.models.audit import AuditEvent
from backend.app.models.user import SessionModel, User
from backend.app.schemas.user import UserCreate, UserUpdate


def list_users(db: Session, admin: User) -> list[User]:
    require_global_admin(admin)
    stmt = select(User).order_by(User.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def create_user(db: Session, admin: User, data: UserCreate) -> User:
    require_global_admin(admin)
    norm_email = data.email.strip().lower()

    existing = db.execute(
        select(User).where(User.email_normalized == norm_email)
    ).scalar_one_or_none()
    if existing:
        raise ValidationErrorException(f"User with email '{norm_email}' already exists.")

    user = User(
        display_name=data.display_name.strip(),
        email_normalized=norm_email,
        password_hash=hash_password(data.password),
        global_role=data.global_role,
        is_active=True,
    )
    db.add(user)
    db.flush()

    audit = AuditEvent(
        actor_id=admin.id,
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        metadata_json=f'{{"email": "{norm_email}", "role": "{user.global_role}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return user


def count_active_admins(db: Session) -> int:
    stmt = select(func.count(User.id)).where(
        User.global_role == GlobalRole.GLOBAL_ADMIN,
        User.is_active.is_(True),
    )
    return db.execute(stmt).scalar() or 0


def update_user(db: Session, admin: User, user_id: int, data: UserUpdate) -> User:
    require_global_admin(admin)
    target = db.get(User, user_id)
    if not target:
        raise ValidationErrorException("Target user not found.")

    if data.global_role and data.global_role != target.global_role:
        if (
            target.global_role == GlobalRole.GLOBAL_ADMIN
            and data.global_role != GlobalRole.GLOBAL_ADMIN
        ):
            if count_active_admins(db) <= 1:
                raise LastAdminProtectionException(
                    "Cannot demote the last active Global Administrator."
                )
        target.global_role = data.global_role
        # Revoke existing sessions immediately on security-sensitive role change
        db.execute(
            update(SessionModel)
            .where(SessionModel.user_id == target.id, SessionModel.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )

    if data.display_name:
        target.display_name = data.display_name.strip()

    audit = AuditEvent(
        actor_id=admin.id,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=str(target.id),
        metadata_json=f'{{"display_name": "{target.display_name}", "role": "{target.global_role}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(target)
    return target


def deactivate_user(db: Session, admin: User, user_id: int) -> User:
    require_global_admin(admin)
    target = db.get(User, user_id)
    if not target:
        raise ValidationErrorException("Target user not found.")

    if target.global_role == GlobalRole.GLOBAL_ADMIN:
        if count_active_admins(db) <= 1:
            raise LastAdminProtectionException(
                "Cannot deactivate the last active Global Administrator."
            )

    target.is_active = False

    # Revoke all active sessions for this user immediately!
    db.execute(
        update(SessionModel)
        .where(SessionModel.user_id == target.id, SessionModel.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )

    audit = AuditEvent(
        actor_id=admin.id,
        action="USER_DEACTIVATED",
        entity_type="user",
        entity_id=str(target.id),
        metadata_json=f'{{"deactivated_user": "{target.email_normalized}"}}',
        request_id=get_request_id(),
    )
    db.add(audit)
    db.commit()
    db.refresh(target)
    return target


def list_audit_events(db: Session, admin: User, limit: int = 50) -> list[dict]:
    require_global_admin(admin)
    stmt = (
        select(AuditEvent, User.display_name)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "actor_name": actor_name or "System",
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "metadata_json": event.metadata_json,
            "timestamp": event.timestamp,
            "request_id": event.request_id,
        }
        for event, actor_name in rows
    ]
