"""System health and safe diagnostics API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.user import User

router = APIRouter(prefix="/system", tags=["System"])


class HealthResponse(BaseModel):
    status: str
    app_env: str
    database_connected: bool
    version: str = "0.1.0"


class SafeDiagnosticsResponse(BaseModel):
    app_env: str
    database_type: str
    token_ttl_hours: int
    login_window_minutes: int
    login_max_failures: int
    max_page_size: int
    reprotrack_api_url: str
    cors_configured_origins_count: int


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        app_env=settings.APP_ENV,
        database_connected=db_ok,
    )


@router.get("/diagnostics", response_model=SafeDiagnosticsResponse)
def get_diagnostics(current_user: User = Depends(get_current_user)):
    """Return safe configuration and runtime metrics without exposing secrets."""
    return SafeDiagnosticsResponse(
        app_env=settings.APP_ENV,
        database_type="SQLite" if settings.is_sqlite else "PostgreSQL",
        token_ttl_hours=settings.TOKEN_TTL_HOURS,
        login_window_minutes=settings.LOGIN_WINDOW_MINUTES,
        login_max_failures=settings.LOGIN_MAX_FAILURES,
        max_page_size=settings.MAX_PAGE_SIZE,
        reprotrack_api_url=settings.REPROTRACK_API_URL,
        cors_configured_origins_count=len(settings.cors_origin_list),
    )
