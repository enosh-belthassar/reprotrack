"""Authentication API routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import extract_bearer_token, get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, LoginResponse, UserSummary
from backend.app.services.auth_service import authenticate_user, revoke_session

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(request_data: LoginRequest, req: Request, db: Session = Depends(get_db)):
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    raw_token, session_obj, user = authenticate_user(
        db=db,
        identifier=request_data.identifier,
        password=request_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return LoginResponse(
        token=raw_token,
        token_type="Bearer",  # nosec: B106
        expires_at=session_obj.expires_at,
        user=UserSummary(
            id=user.id,
            display_name=user.display_name,
            email_normalized=user.email_normalized,
            global_role=user.global_role,
            is_active=user.is_active,
        ),
    )


@router.post("/logout")
def logout(
    token: str = Depends(extract_bearer_token),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_session(db, token)
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserSummary)
def get_me(current_user: User = Depends(get_current_user)):
    return UserSummary(
        id=current_user.id,
        display_name=current_user.display_name,
        email_normalized=current_user.email_normalized,
        global_role=current_user.global_role,
        is_active=current_user.is_active,
    )
