"""Dashboard metrics API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.dashboard import ActivityEvent, DashboardSummary
from backend.app.services.report_service import get_dashboard_summary, get_recent_activity

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db, current_user)


@router.get("/recent-activity", response_model=list[ActivityEvent])
def get_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_recent_activity(db, current_user)
