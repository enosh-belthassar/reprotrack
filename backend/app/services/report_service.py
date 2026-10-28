"""Dashboard metrics and analytical reports computation services."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.db_utils import utc_now
from backend.app.core.permissions import ensure_project_access, is_global_admin
from backend.app.models.issue import Issue, IssueEvent, VerificationRun
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User


def get_accessible_project_ids(db: Session, user: User) -> list[int] | None:
    if is_global_admin(user):
        return None
    stmt = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    return list(db.execute(stmt).scalars().all())


def apply_project_scope(
    query, model, accessible_ids: list[int] | None, project_id: int | None = None
):
    if project_id:
        return query.where(model.project_id == project_id)
    if accessible_ids is not None:
        if not accessible_ids:
            return query.where(model.id == -1)
        return query.where(model.project_id.in_(accessible_ids))
    return query


def get_dashboard_summary(db: Session, user: User) -> dict:
    accessible_ids = get_accessible_project_ids(db, user)

    # 1. Project count
    if accessible_ids is None:
        proj_count = (
            db.execute(select(func.count(Project.id)).where(Project.is_active.is_(True))).scalar()
            or 0
        )
    else:
        proj_count = len(accessible_ids)

    base_query = apply_project_scope(select(Issue), Issue, accessible_ids)

    # Open count
    open_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(Issue.status.not_in(["CLOSED", "WONT_FIX"])).subquery()
            )
        ).scalar()
        or 0
    )

    # Critical/High count
    crit_high_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(
                    Issue.status.not_in(["CLOSED", "WONT_FIX"]),
                    Issue.severity.in_(["HIGH", "CRITICAL"]),
                ).subquery()
            )
        ).scalar()
        or 0
    )

    # In progress
    in_prog_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(Issue.status == "IN_PROGRESS").subquery()
            )
        ).scalar()
        or 0
    )

    # Fixed awaiting verification
    fixed_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(Issue.status.in_(["FIXED", "IN_VERIFICATION"])).subquery()
            )
        ).scalar()
        or 0
    )

    # Reopened
    reopened_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(Issue.status == "REOPENED").subquery()
            )
        ).scalar()
        or 0
    )

    # Overdue
    now = utc_now()
    overdue_count = (
        db.execute(
            select(func.count()).select_from(
                base_query.where(
                    Issue.status.not_in(["CLOSED", "WONT_FIX"]),
                    Issue.due_at.is_not(None),
                    Issue.due_at < now,
                ).subquery()
            )
        ).scalar()
        or 0
    )

    return {
        "accessible_projects_count": proj_count,
        "open_issues_count": open_count,
        "critical_high_count": crit_high_count,
        "in_progress_count": in_prog_count,
        "fixed_awaiting_verification_count": fixed_count,
        "reopened_count": reopened_count,
        "overdue_count": overdue_count,
    }


def get_recent_activity(db: Session, user: User, limit: int = 15) -> list[dict]:
    accessible_ids = get_accessible_project_ids(db, user)

    stmt = (
        select(IssueEvent, Issue.issue_key, Issue.title, User.display_name)
        .join(Issue, Issue.id == IssueEvent.issue_id)
        .outerjoin(User, User.id == IssueEvent.actor_id)
    )
    if accessible_ids is not None:
        if not accessible_ids:
            return []
        stmt = stmt.where(Issue.project_id.in_(accessible_ids))

    stmt = stmt.order_by(IssueEvent.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()

    return [
        {
            "id": event.id,
            "issue_key": key,
            "issue_title": title,
            "actor_name": actor_name or "System",
            "event_type": event.event_type,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "timestamp": event.created_at,
        }
        for event, key, title, actor_name in rows
    ]


def get_status_breakdown(db: Session, user: User, project_id: int | None = None) -> list[dict]:
    if project_id:
        ensure_project_access(db, project_id, user)
    accessible_ids = get_accessible_project_ids(db, user)

    stmt = select(Issue.status, func.count(Issue.id)).group_by(Issue.status)
    stmt = apply_project_scope(stmt, Issue, accessible_ids, project_id)
    rows = db.execute(stmt).all()
    return [{"status": r[0], "count": r[1]} for r in rows]


def get_severity_breakdown(db: Session, user: User, project_id: int | None = None) -> list[dict]:
    if project_id:
        ensure_project_access(db, project_id, user)
    accessible_ids = get_accessible_project_ids(db, user)

    stmt = select(Issue.severity, func.count(Issue.id)).group_by(Issue.severity)
    stmt = apply_project_scope(stmt, Issue, accessible_ids, project_id)
    rows = db.execute(stmt).all()
    return [{"severity": r[0], "count": r[1]} for r in rows]


def get_resolution_time_metrics(db: Session, user: User, project_id: int | None = None) -> dict:
    if project_id:
        ensure_project_access(db, project_id, user)
    accessible_ids = get_accessible_project_ids(db, user)

    stmt = select(Issue.created_at, Issue.resolved_at).where(Issue.resolved_at.is_not(None))
    stmt = apply_project_scope(stmt, Issue, accessible_ids, project_id)
    rows = db.execute(stmt).all()

    if not rows:
        return {"average_hours": 0.0, "median_hours": 0.0, "resolved_count": 0}

    durations = []
    for r in rows:
        created = r[0]
        resolved = r[1]
        if created and resolved:
            if created.tzinfo is None and resolved.tzinfo is not None:
                created = created.replace(tzinfo=resolved.tzinfo)
            elif resolved.tzinfo is None and created.tzinfo is not None:
                resolved = resolved.replace(tzinfo=created.tzinfo)
            if resolved > created:
                durations.append((resolved - created).total_seconds() / 3600.0)

    if not durations:
        return {"average_hours": 0.0, "median_hours": 0.0, "resolved_count": 0}

    durations.sort()
    avg_hours = round(sum(durations) / len(durations), 1)
    mid = len(durations) // 2
    median_hours = round(
        durations[mid] if len(durations) % 2 != 0 else (durations[mid - 1] + durations[mid]) / 2, 1
    )

    return {
        "average_hours": avg_hours,
        "median_hours": median_hours,
        "resolved_count": len(durations),
    }


def get_reopened_rate_metrics(db: Session, user: User, project_id: int | None = None) -> dict:
    if project_id:
        ensure_project_access(db, project_id, user)
    accessible_ids = get_accessible_project_ids(db, user)

    # Verification runs on accessible issues
    stmt = select(VerificationRun.result).join(Issue, Issue.id == VerificationRun.issue_id)
    stmt = apply_project_scope(stmt, Issue, accessible_ids, project_id)
    runs = db.execute(stmt).scalars().all()

    total_runs = len(runs)
    failed_runs = sum(1 for r in runs if r == "FAIL")

    rate = round((failed_runs / total_runs * 100.0), 1) if total_runs > 0 else 0.0

    return {
        "reopened_count": failed_runs,
        "total_verified_count": total_runs,
        "reopened_rate_percentage": rate,
    }


def get_backlog_age_metrics(db: Session, user: User, project_id: int | None = None) -> dict:
    if project_id:
        ensure_project_access(db, project_id, user)
    accessible_ids = get_accessible_project_ids(db, user)

    now = utc_now()
    stmt = select(Issue.created_at).where(Issue.status.not_in(["CLOSED", "WONT_FIX"]))
    stmt = apply_project_scope(stmt, Issue, accessible_ids, project_id)
    created_dates = db.execute(stmt).scalars().all()

    under_7 = 0
    from_7_to_30 = 0
    over_30 = 0

    for cd in created_dates:
        cd_tz = cd.replace(tzinfo=now.tzinfo) if cd.tzinfo is None else cd
        age_days = (now - cd_tz).days
        if age_days < 7:
            under_7 += 1
        elif age_days <= 30:
            from_7_to_30 += 1
        else:
            over_30 += 1

    return {
        "under_7_days": under_7,
        "from_7_to_30_days": from_7_to_30,
        "over_30_days": over_30,
        "total_open": len(created_dates),
    }
