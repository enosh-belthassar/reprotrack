"""Issues, comments, lifecycle transitions, and events API routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.issue import Issue
from backend.app.models.user import User
from backend.app.schemas.issue import (
    IssueAssign,
    IssueCommentCreate,
    IssueCommentResponse,
    IssueCreate,
    IssueEventResponse,
    IssueListResponse,
    IssueResponse,
    IssueTransition,
    IssueUpdate,
    VerificationCreate,
    VerificationResponse,
)
from backend.app.services.issue_service import (
    add_issue_comment,
    assign_issue,
    create_issue,
    get_issue,
    list_issues,
    record_verification,
    transition_issue_status,
    update_issue_metadata,
)

router = APIRouter(prefix="/issues", tags=["Issues"])


def serialize_issue(issue: Issue) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        issue_key=issue.issue_key,
        project_id=issue.project_id,
        project_key=issue.project.key if issue.project else "",
        project_name=issue.project.name if issue.project else "",
        title=issue.title,
        description=issue.description,
        steps_to_reproduce=issue.steps_to_reproduce,
        expected_result=issue.expected_result,
        actual_result=issue.actual_result,
        environment=issue.environment,
        severity=issue.severity,
        priority=issue.priority,
        status=issue.status,
        reporter_id=issue.reporter_id,
        reporter_name=issue.reporter.display_name if issue.reporter else "",
        assignee_id=issue.assignee_id,
        assignee_name=issue.assignee.display_name if issue.assignee else None,
        version=issue.version,
        due_at=issue.due_at,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        resolved_at=issue.resolved_at,
        closed_at=issue.closed_at,
    )


@router.get("", response_model=IssueListResponse)
def get_issues(
    project_id: int | None = Query(None),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=settings.MAX_PAGE_SIZE),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issues, total = list_issues(
        db=db,
        user=current_user,
        project_id=project_id,
        status=status,
        severity=severity,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return IssueListResponse(
        items=[serialize_issue(i) for i in issues],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def post_issue(
    data: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = create_issue(db, current_user, data)
    return serialize_issue(issue)


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue_detail(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = get_issue(db, current_user, issue_id)
    return serialize_issue(issue)


@router.patch("/{issue_id}", response_model=IssueResponse)
def patch_issue(
    issue_id: int,
    data: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = update_issue_metadata(db, current_user, issue_id, data)
    return serialize_issue(issue)


@router.post("/{issue_id}/assign", response_model=IssueResponse)
def post_assign(
    issue_id: int,
    data: IssueAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = assign_issue(db, current_user, issue_id, data.assignee_id, data.version)
    return serialize_issue(issue)


@router.post("/{issue_id}/transition", response_model=IssueResponse)
def post_transition(
    issue_id: int,
    data: IssueTransition,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = transition_issue_status(db, current_user, issue_id, data)
    return serialize_issue(issue)


@router.get("/{issue_id}/comments", response_model=list[IssueCommentResponse])
def get_comments(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = get_issue(db, current_user, issue_id)
    return [
        IssueCommentResponse(
            id=c.id,
            issue_id=c.issue_id,
            author_id=c.author_id,
            author_name=c.author.display_name if c.author else "",
            body=c.body,
            created_at=c.created_at,
        )
        for c in issue.comments
    ]


@router.post(
    "/{issue_id}/comments", response_model=IssueCommentResponse, status_code=status.HTTP_201_CREATED
)
def post_comment(
    issue_id: int,
    data: IssueCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = add_issue_comment(db, current_user, issue_id, data)
    return IssueCommentResponse(
        id=comment.id,
        issue_id=comment.issue_id,
        author_id=comment.author_id,
        author_name=comment.author.display_name if comment.author else "",
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/{issue_id}/events", response_model=list[IssueEventResponse])
def get_events(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = get_issue(db, current_user, issue_id)
    return [
        IssueEventResponse(
            id=e.id,
            issue_id=e.issue_id,
            actor_id=e.actor_id,
            actor_name=e.actor.display_name if e.actor else "System",
            event_type=e.event_type,
            old_value=e.old_value,
            new_value=e.new_value,
            details=e.details,
            created_at=e.created_at,
            request_id=e.request_id,
        )
        for e in issue.events
    ]


@router.get("/{issue_id}/verifications", response_model=list[VerificationResponse])
def get_verifications(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = get_issue(db, current_user, issue_id)
    return [
        VerificationResponse(
            id=v.id,
            issue_id=v.issue_id,
            tester_id=v.tester_id,
            tester_name=v.tester.display_name if v.tester else "",
            result=v.result,
            test_notes=v.test_notes,
            tested_version=v.tested_version,
            created_at=v.created_at,
        )
        for v in issue.verification_runs
    ]


@router.post(
    "/{issue_id}/verify", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED
)
def post_verification(
    issue_id: int,
    data: VerificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run, issue = record_verification(db, current_user, issue_id, data)
    return VerificationResponse(
        id=run.id,
        issue_id=run.issue_id,
        tester_id=run.tester_id,
        tester_name=run.tester.display_name if run.tester else "",
        result=run.result,
        test_notes=run.test_notes,
        tested_version=run.tested_version,
        created_at=run.created_at,
    )
