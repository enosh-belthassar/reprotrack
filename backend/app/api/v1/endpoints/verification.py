"""Fix verification API routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.api.v1.endpoints.issues import serialize_issue
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.issue import (
    IssueResponse,
    VerificationCreate,
    VerificationResponse,
)
from backend.app.services.issue_service import list_issues, record_verification

router = APIRouter(prefix="/verification", tags=["Verification"])


@router.get("/pending", response_model=list[IssueResponse])
def get_pending_verifications(
    project_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve issues currently in FIXED or IN_VERIFICATION status awaiting test verification."""
    # Retrieve FIXED issues
    fixed_issues, _ = list_issues(
        db=db,
        user=current_user,
        project_id=project_id,
        status="FIXED",
        page=1,
        page_size=100,
        sort_by="updated_at",
        sort_dir="desc",
    )
    # Retrieve IN_VERIFICATION issues
    in_verif_issues, _ = list_issues(
        db=db,
        user=current_user,
        project_id=project_id,
        status="IN_VERIFICATION",
        page=1,
        page_size=100,
        sort_by="updated_at",
        sort_dir="desc",
    )
    combined = list(fixed_issues) + list(in_verif_issues)
    return [serialize_issue(i) for i in combined]


@router.post(
    "/{issue_id}", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED
)
def submit_verification(
    issue_id: int,
    data: VerificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a PASS or FAIL fix verification run for an issue."""
    run, _ = record_verification(db, current_user, issue_id, data)
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
