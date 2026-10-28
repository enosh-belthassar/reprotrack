"""Reports and Dashboard schemas."""

from datetime import datetime

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class ResolutionTimeMetrics(BaseModel):
    average_hours: float
    median_hours: float
    resolved_count: int


class ReopenedRateMetrics(BaseModel):
    reopened_count: int
    total_verified_count: int
    reopened_rate_percentage: float


class BacklogAgeMetrics(BaseModel):
    under_7_days: int
    from_7_to_30_days: int
    over_30_days: int
    total_open: int


class DashboardSummary(BaseModel):
    accessible_projects_count: int
    open_issues_count: int
    critical_high_count: int
    in_progress_count: int
    fixed_awaiting_verification_count: int
    reopened_count: int
    overdue_count: int


class ActivityEvent(BaseModel):
    id: int
    issue_key: str
    issue_title: str
    actor_name: str
    event_type: str
    old_value: str | None
    new_value: str | None
    timestamp: datetime
