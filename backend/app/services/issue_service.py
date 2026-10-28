"""Issue lifecycle, atomic state transitions, comments, and fix verification services."""

import json

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.db_utils import utc_now
from backend.app.core.exceptions import (
    ConcurrentModificationException,
    InvalidStatusTransitionException,
    IssueNotFoundException,
    ValidationErrorException,
)
from backend.app.core.permissions import (
    COMMENT_CREATOR_ROLES,
    ISSUE_CREATOR_ROLES,
    TRIAGE_ROLES,
    VERIFICATION_ROLES,
    ProjectRole,
    ensure_project_access,
    is_global_admin,
    require_project_role,
    validate_fix_verification_tester,
)
from backend.app.core.request_context import get_request_id
from backend.app.models.issue import Issue, IssueComment, IssueEvent, VerificationRun
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User
from backend.app.schemas.issue import (
    IssueCommentCreate,
    IssueCreate,
    IssueTransition,
    IssueUpdate,
    VerificationCreate,
)

# Valid status transitions map
VALID_TRANSITIONS = {
    "REPORTED": {"TRIAGED"},
    "TRIAGED": {"IN_PROGRESS", "WONT_FIX"},
    "IN_PROGRESS": {"FIXED"},
    "FIXED": {"IN_VERIFICATION"},
    "IN_VERIFICATION": {
        "CLOSED",
        "REOPENED",
    },  # CLOSED only via passing verification, REOPENED on fail
    "REOPENED": {"IN_PROGRESS"},
    "WONT_FIX": {"TRIAGED"},  # Requires reason and privileged role
    "CLOSED": {"REOPENED"},  # Requires reason and privileged role
}


def generate_issue_key(db: Session, project: Project) -> str:
    """Generate next issue key safely using database-backed sequencing."""
    seq = project.next_issue_number
    project.next_issue_number += 1
    db.flush()
    return f"{project.key}-{seq}"


def create_issue(db: Session, user: User, data: IssueCreate) -> Issue:
    # 1. Check project access & permission
    require_project_role(db, data.project_id, user, ISSUE_CREATOR_ROLES)
    from backend.app.core.config import settings

    stmt = select(Project).where(Project.id == data.project_id)
    if not settings.is_sqlite:
        stmt = stmt.with_for_update()
    project = db.execute(stmt).scalar_one_or_none()
    if not project or not project.is_active:
        raise ValidationErrorException("Project is inactive or not found.")

    # 2. Assignee check if provided
    assignee_id = None
    if data.assignee_id:
        assignee = db.get(User, data.assignee_id)
        if not assignee or not assignee.is_active:
            raise ValidationErrorException("Assignee user is not found or inactive.")
        ensure_project_access(db, data.project_id, assignee)
        assignee_id = assignee.id

    # 3. Create issue with server-generated key
    key = generate_issue_key(db, project)

    issue = Issue(
        issue_key=key,
        project_id=project.id,
        title=data.title.strip(),
        description=data.description.strip(),
        steps_to_reproduce=data.steps_to_reproduce.strip(),
        expected_result=data.expected_result.strip(),
        actual_result=data.actual_result.strip(),
        environment=data.environment.strip() if data.environment else None,
        severity=data.severity,
        priority=data.priority,
        status="REPORTED",
        reporter_id=user.id,
        assignee_id=assignee_id,
        version=1,
        due_at=data.due_at,
    )
    db.add(issue)
    db.flush()

    # Append event
    event = IssueEvent(
        issue_id=issue.id,
        actor_id=user.id,
        event_type="CREATED",
        new_value="REPORTED",
        details=json.dumps(
            {"title": issue.title, "severity": issue.severity, "priority": issue.priority}
        ),
        request_id=get_request_id(),
    )
    db.add(event)
    db.commit()
    db.refresh(issue)
    return issue


def get_issue(db: Session, user: User, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise IssueNotFoundException()
    ensure_project_access(db, issue.project_id, user)
    return issue


def update_issue_metadata(db: Session, user: User, issue_id: int, data: IssueUpdate) -> Issue:
    issue = get_issue(db, user, issue_id)

    # Optimistic concurrency check
    if issue.version != data.version:
        raise ConcurrentModificationException()

    # Triage permissions required for severity / priority changes
    if data.severity or data.priority:
        require_project_role(db, issue.project_id, user, TRIAGE_ROLES)

    changes = {}
    if data.title is not None and data.title.strip() != issue.title:
        changes["title"] = {"old": issue.title, "new": data.title.strip()}
        issue.title = data.title.strip()
    if data.description is not None:
        issue.description = data.description.strip()
    if data.steps_to_reproduce is not None:
        issue.steps_to_reproduce = data.steps_to_reproduce.strip()
    if data.expected_result is not None:
        issue.expected_result = data.expected_result.strip()
    if data.actual_result is not None:
        issue.actual_result = data.actual_result.strip()
    if data.environment is not None:
        issue.environment = data.environment.strip() if data.environment else None
    if data.severity is not None and data.severity != issue.severity:
        changes["severity"] = {"old": issue.severity, "new": data.severity}
        issue.severity = data.severity
    if data.priority is not None and data.priority != issue.priority:
        changes["priority"] = {"old": issue.priority, "new": data.priority}
        issue.priority = data.priority
    if data.due_at is not None:
        issue.due_at = data.due_at

    issue.version += 1
    issue.updated_at = utc_now()

    if changes:
        event = IssueEvent(
            issue_id=issue.id,
            actor_id=user.id,
            event_type="METADATA_UPDATED",
            details=json.dumps(changes),
            request_id=get_request_id(),
        )
        db.add(event)

    db.commit()
    db.refresh(issue)
    return issue


def assign_issue(
    db: Session, user: User, issue_id: int, assignee_id: int | None, version: int
) -> Issue:
    issue = get_issue(db, user, issue_id)
    if issue.version != version:
        raise ConcurrentModificationException()

    require_project_role(db, issue.project_id, user, TRIAGE_ROLES)

    old_assignee = issue.assignee.display_name if issue.assignee else "Unassigned"
    new_assignee_name = "Unassigned"

    if assignee_id is not None:
        target_user = db.get(User, assignee_id)
        if not target_user or not target_user.is_active:
            raise ValidationErrorException("Target assignee not found or inactive.")
        ensure_project_access(db, issue.project_id, target_user)
        issue.assignee_id = target_user.id
        new_assignee_name = target_user.display_name
    else:
        issue.assignee_id = None

    issue.version += 1
    issue.updated_at = utc_now()

    event = IssueEvent(
        issue_id=issue.id,
        actor_id=user.id,
        event_type="ASSIGNED",
        old_value=old_assignee,
        new_value=new_assignee_name,
        request_id=get_request_id(),
    )
    db.add(event)
    db.commit()
    db.refresh(issue)
    return issue


def transition_issue_status(
    db: Session,
    user: User,
    issue_id: int,
    transition: IssueTransition,
) -> Issue:
    """Atomic issue state transitions with role and invariant enforcement."""
    issue = get_issue(db, user, issue_id)

    # 1. Concurrency check
    if issue.version != transition.version:
        raise ConcurrentModificationException()

    curr_status = issue.status
    new_status = transition.new_status

    # 2. Check transition graph validity
    allowed = VALID_TRANSITIONS.get(curr_status, set())
    if new_status not in allowed:
        raise InvalidStatusTransitionException(
            f"Transition from {curr_status} to {new_status} is not allowed."
        )

    # 3. Invariant: IN_VERIFICATION -> CLOSED or REOPENED can only happen via record_verification!
    if curr_status == "IN_VERIFICATION" and new_status in {"CLOSED", "REOPENED"}:
        raise InvalidStatusTransitionException(
            "Closing or reopening an issue in verification must be done via fix verification."
        )

    # 4. Role authorization for specific transitions
    ensure_project_access(db, issue.project_id, user)
    clean_reason = transition.reason.strip() if transition.reason else ""

    if new_status == "TRIAGED":
        # Can only be done by triage roles
        require_project_role(db, issue.project_id, user, TRIAGE_ROLES)
        if curr_status == "WONT_FIX" and not clean_reason:
            raise ValidationErrorException(
                "A non-empty reason is required to move a WONT_FIX issue back to TRIAGED."
            )
    elif new_status == "WONT_FIX":
        require_project_role(
            db, issue.project_id, user, {ProjectRole.PROJECT_ADMIN, ProjectRole.TESTER}
        )
        if not clean_reason:
            raise ValidationErrorException(
                "A non-empty reason is required to mark an issue as WONT_FIX."
            )
    elif new_status == "IN_PROGRESS":
        # Can be moved by assignee, developer, or triage role
        require_project_role(
            db,
            issue.project_id,
            user,
            {ProjectRole.PROJECT_ADMIN, ProjectRole.DEVELOPER, ProjectRole.TESTER},
        )
    elif new_status == "FIXED":
        # Developer or assignee completes the fix
        require_project_role(
            db, issue.project_id, user, {ProjectRole.PROJECT_ADMIN, ProjectRole.DEVELOPER}
        )
    elif new_status == "IN_VERIFICATION":
        # Tester moves it to in_verification
        require_project_role(db, issue.project_id, user, VERIFICATION_ROLES)
    elif curr_status == "CLOSED" and new_status == "REOPENED":
        require_project_role(
            db, issue.project_id, user, {ProjectRole.PROJECT_ADMIN, ProjectRole.TESTER}
        )
        if not clean_reason:
            raise ValidationErrorException(
                "A non-empty reason is required to reopen a closed issue."
            )

    # 5. Apply state change atomically
    issue.status = new_status
    issue.version += 1
    issue.updated_at = utc_now()

    if new_status == "FIXED":
        issue.resolved_at = utc_now()
    elif new_status == "CLOSED":
        issue.closed_at = utc_now()

    event = IssueEvent(
        issue_id=issue.id,
        actor_id=user.id,
        event_type="STATUS_CHANGED",
        old_value=curr_status,
        new_value=new_status,
        details=clean_reason or None,
        request_id=get_request_id(),
    )
    db.add(event)
    db.commit()
    db.refresh(issue)
    return issue


def record_verification(
    db: Session,
    tester: User,
    issue_id: int,
    data: VerificationCreate,
) -> tuple[VerificationRun, Issue]:
    """Execute fix verification run with separation of duties and atomic status update."""
    issue = get_issue(db, tester, issue_id)

    # 1. State check: Issue must be in FIXED or IN_VERIFICATION
    if issue.status not in {"FIXED", "IN_VERIFICATION"}:
        raise InvalidStatusTransitionException(
            f"Fix verification can only be performed on issues in FIXED or IN_VERIFICATION status (current: {issue.status})."
        )

    # 2. Separation of duties: Developer / assignee cannot verify their own fix
    validate_fix_verification_tester(tester, issue)

    # 3. Permission check: Tester role or Project Admin or Global Admin
    require_project_role(db, issue.project_id, tester, VERIFICATION_ROLES)

    # 4. Save verification run (immutable)
    run = VerificationRun(
        issue_id=issue.id,
        tester_id=tester.id,
        result=data.result,
        test_notes=data.test_notes.strip(),
        tested_version=data.tested_version.strip(),
    )
    db.add(run)

    old_status = issue.status
    if data.result == "PASS":
        # Pass -> CLOSED
        issue.status = "CLOSED"
        issue.closed_at = utc_now()
        event_type = "VERIFICATION_PASSED"
    else:
        # Fail -> REOPENED
        issue.status = "REOPENED"
        issue.resolved_at = None
        event_type = "VERIFICATION_FAILED"

    issue.version += 1
    issue.updated_at = utc_now()

    event = IssueEvent(
        issue_id=issue.id,
        actor_id=tester.id,
        event_type=event_type,
        old_value=old_status,
        new_value=issue.status,
        details=json.dumps(
            {
                "result": data.result,
                "version": data.tested_version,
                "notes": data.test_notes,
            }
        ),
        request_id=get_request_id(),
    )
    db.add(event)
    db.commit()
    db.refresh(run)
    db.refresh(issue)
    return run, issue


def add_issue_comment(
    db: Session, user: User, issue_id: int, data: IssueCommentCreate
) -> IssueComment:
    issue = get_issue(db, user, issue_id)
    require_project_role(db, issue.project_id, user, COMMENT_CREATOR_ROLES)
    comment = IssueComment(
        issue_id=issue.id,
        author_id=user.id,
        body=data.body.strip(),
    )
    db.add(comment)

    event = IssueEvent(
        issue_id=issue.id,
        actor_id=user.id,
        event_type="COMMENT_ADDED",
        details=comment.body[:100],
        request_id=get_request_id(),
    )
    db.add(event)
    db.commit()
    db.refresh(comment)
    return comment


def list_issues(
    db: Session,
    user: User,
    project_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> tuple[list[Issue], int]:
    # 1. Enforce accessible project scope
    if is_global_admin(user):
        accessible_project_ids = None
    else:
        stmt_proj = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        accessible_project_ids = list(db.execute(stmt_proj).scalars().all())

    # 2. Build query
    query = select(Issue)

    if project_id:
        # Check that user can access this specific project
        ensure_project_access(db, project_id, user)
        query = query.where(Issue.project_id == project_id)
    elif accessible_project_ids is not None:
        if not accessible_project_ids:
            return [], 0
        query = query.where(Issue.project_id.in_(accessible_project_ids))

    if status:
        query = query.where(Issue.status == status)
    if severity:
        query = query.where(Issue.severity == severity)
    if priority:
        query = query.where(Issue.priority == priority)
    if assignee_id:
        query = query.where(Issue.assignee_id == assignee_id)
    if search:
        search_pat = f"%{search.strip()}%"
        query = query.where(
            or_(
                Issue.issue_key.ilike(search_pat),
                Issue.title.ilike(search_pat),
                Issue.description.ilike(search_pat),
            )
        )

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Allowlisted sorting
    allowed_sorts = {
        "created_at": Issue.created_at,
        "updated_at": Issue.updated_at,
        "severity": Issue.severity,
        "priority": Issue.priority,
        "status": Issue.status,
        "issue_key": Issue.issue_key,
    }
    sort_col = allowed_sorts.get(sort_by, Issue.created_at)
    order_func = desc if sort_dir.lower() == "desc" else asc
    query = query.order_by(order_func(sort_col))

    # Pagination
    limit = min(page_size, 100)
    offset = (max(page, 1) - 1) * limit
    query = query.offset(offset).limit(limit)

    issues = db.execute(query).scalars().all()
    return issues, total
