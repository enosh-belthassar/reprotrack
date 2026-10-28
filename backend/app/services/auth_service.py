"""Authentication service with database-backed throttling and opaque sessions."""

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.db_utils import utc_now
from backend.app.core.exceptions import (
    InvalidCredentialsException,
    LoginThrottledException,
    UnauthorizedException,
    UserInactiveException,
)
from backend.app.core.security import (
    dummy_verify_password,
    generate_opaque_token,
    hash_token,
    verify_password,
)
from backend.app.models.user import LoginAttempt, SessionModel, User


def normalize_identifier(identifier: str) -> str:
    return identifier.strip().lower()


def check_login_throttling(db: Session, norm_ident: str) -> None:
    window_start = utc_now() - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    stmt = select(func.count(LoginAttempt.id)).where(
        LoginAttempt.identifier == norm_ident,
        LoginAttempt.result == "FAILED",
        LoginAttempt.timestamp >= window_start,
    )
    failed_count = db.execute(stmt).scalar() or 0
    if failed_count >= settings.LOGIN_MAX_FAILURES:
        raise LoginThrottledException(
            f"Too many failed login attempts ({failed_count}). Please try again after {settings.LOGIN_WINDOW_MINUTES} minutes."
        )


def record_login_attempt(db: Session, norm_ident: str, result: str, ip: str | None = None) -> None:
    attempt = LoginAttempt(
        identifier=norm_ident,
        result=result,
        ip_address=ip,
        timestamp=utc_now(),
    )
    db.add(attempt)
    db.commit()


def cleanup_old_attempts(db: Session) -> None:
    retention_cutoff = utc_now() - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES * 4)
    db.execute(delete(LoginAttempt).where(LoginAttempt.timestamp < retention_cutoff))
    db.commit()


def authenticate_user(
    db: Session,
    identifier: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, SessionModel, User]:
    norm_ident = normalize_identifier(identifier)

    # 1. Check throttling before password evaluation
    check_login_throttling(db, norm_ident)

    # 2. Query user by normalized email
    stmt = select(User).where(User.email_normalized == norm_ident)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        dummy_verify_password(password)
        record_login_attempt(db, norm_ident, "FAILED", ip_address)
        raise InvalidCredentialsException()

    # 3. Verify password
    if not verify_password(password, user.password_hash):
        record_login_attempt(db, norm_ident, "FAILED", ip_address)
        raise InvalidCredentialsException()

    # 4. Check active state
    if not user.is_active:
        raise UserInactiveException()

    # 5. Success: record attempt and cleanup
    record_login_attempt(db, norm_ident, "SUCCESS", ip_address)
    cleanup_old_attempts(db)

    # 6. Issue high-entropy opaque session token
    raw_token = generate_opaque_token()
    token_hash_val = hash_token(raw_token)
    expires_at = utc_now() + timedelta(hours=settings.TOKEN_TTL_HOURS)

    session_obj = SessionModel(
        user_id=user.id,
        token_hash=token_hash_val,
        expires_at=expires_at,
        user_agent=user_agent[:250] if user_agent else None,
    )
    user.last_login_at = utc_now()
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)

    return raw_token, session_obj, user


def revoke_session(db: Session, raw_token: str) -> None:
    token_hash_val = hash_token(raw_token)
    stmt = select(SessionModel).where(SessionModel.token_hash == token_hash_val)
    session_obj = db.execute(stmt).scalar_one_or_none()
    if session_obj:
        session_obj.revoked_at = utc_now()
        db.commit()


def get_user_by_token(db: Session, raw_token: str) -> User:
    token_hash_val = hash_token(raw_token)
    stmt = select(SessionModel).where(
        SessionModel.token_hash == token_hash_val,
        SessionModel.revoked_at.is_(None),
    )
    session_obj = db.execute(stmt).scalar_one_or_none()
    if not session_obj or not session_obj.is_valid:
        raise UnauthorizedException("Session is invalid or has expired.")

    user = db.get(User, session_obj.user_id)
    if not user or not user.is_active:
        raise UserInactiveException()

    return user
