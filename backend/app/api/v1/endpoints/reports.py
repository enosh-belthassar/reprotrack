"""Analytical reports API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    BacklogAgeMetrics,
    ReopenedRateMetrics,
    ResolutionTimeMetrics,
    SeverityCount,
    StatusCount,
)
from backend.app.services.report_service import (
    get_backlog_age_metrics,
    get_reopened_rate_metrics,
    get_resolution_time_metrics,
    get_severity_breakdown,
    get_status_breakdown,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/status-breakdown", response_model=list[StatusCount])
def status_breakdown(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_status_breakdown(db, current_user, project_id)


@router.get("/severity-breakdown", response_model=list[SeverityCount])
def severity_breakdown(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_severity_breakdown(db, current_user, project_id)


@router.get("/resolution-time", response_model=ResolutionTimeMetrics)
def resolution_time(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_resolution_time_metrics(db, current_user, project_id)


@router.get("/reopened-rate", response_model=ReopenedRateMetrics)
def reopened_rate(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_reopened_rate_metrics(db, current_user, project_id)


@router.get("/backlog-age", response_model=BacklogAgeMetrics)
def backlog_age(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_backlog_age_metrics(db, current_user, project_id)
