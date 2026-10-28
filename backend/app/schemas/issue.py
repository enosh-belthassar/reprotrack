"""Issue, Comment, Event, and Verification schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

SEVERITY_PATTERN = "^(LOW|MEDIUM|HIGH|CRITICAL)$"
PRIORITY_PATTERN = "^(LOW|NORMAL|HIGH|URGENT)$"
STATUS_PATTERN = "^(REPORTED|TRIAGED|IN_PROGRESS|FIXED|IN_VERIFICATION|CLOSED|REOPENED|WONT_FIX)$"


class IssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(default="", max_length=10000)
    steps_to_reproduce: str = Field(default="", max_length=10000)
    expected_result: str = Field(default="", max_length=5000)
    actual_result: str = Field(default="", max_length=5000)
    environment: str | None = Field(None, max_length=255)
    severity: str = Field(default="MEDIUM", pattern=SEVERITY_PATTERN)
    priority: str = Field(default="NORMAL", pattern=PRIORITY_PATTERN)
    assignee_id: int | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 3:
            raise ValueError("Issue title cannot be whitespace-only or shorter than 3 characters.")
        return clean


class IssueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None, max_length=10000)
    steps_to_reproduce: str | None = Field(None, max_length=10000)
    expected_result: str | None = Field(None, max_length=5000)
    actual_result: str | None = Field(None, max_length=5000)
    environment: str | None = Field(None, max_length=255)
    severity: str | None = Field(None, pattern=SEVERITY_PATTERN)
    priority: str | None = Field(None, pattern=PRIORITY_PATTERN)
    due_at: datetime | None = None
    version: int = Field(..., description="Optimistic concurrency control version")

    @field_validator("title")
    @classmethod
    def validate_title_optional(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 3:
                raise ValueError(
                    "Issue title cannot be whitespace-only or shorter than 3 characters."
                )
            return clean
        return None


class IssueAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: int | None = None
    version: int = Field(..., description="Optimistic concurrency control version")


class IssueTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: str = Field(..., pattern=STATUS_PATTERN)
    reason: str | None = Field(None, max_length=1000)
    version: int = Field(..., description="Optimistic concurrency control version")


class IssueCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(..., min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Comment body cannot be blank or whitespace-only.")
        return clean


class IssueCommentResponse(BaseModel):
    id: int
    issue_id: int
    author_id: int
    author_name: str
    body: str
    created_at: datetime


class IssueEventResponse(BaseModel):
    id: int
    issue_id: int
    actor_id: int | None
    actor_name: str | None
    event_type: str
    old_value: str | None
    new_value: str | None
    details: str | None
    created_at: datetime
    request_id: str | None


class VerificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: str = Field(..., pattern="^(PASS|FAIL)$")
    test_notes: str = Field(..., min_length=3, max_length=5000)
    tested_version: str = Field(..., min_length=1, max_length=50)

    @field_validator("test_notes")
    @classmethod
    def validate_test_notes(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 3:
            raise ValueError("Test notes cannot be whitespace-only or shorter than 3 characters.")
        return clean

    @field_validator("tested_version")
    @classmethod
    def validate_tested_version(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Tested version cannot be blank or whitespace-only.")
        return clean


class VerificationResponse(BaseModel):
    id: int
    issue_id: int
    tester_id: int
    tester_name: str
    result: str
    test_notes: str
    tested_version: str
    created_at: datetime


class IssueResponse(BaseModel):
    id: int
    issue_key: str
    project_id: int
    project_key: str
    project_name: str
    title: str
    description: str
    steps_to_reproduce: str
    expected_result: str
    actual_result: str
    environment: str | None
    severity: str
    priority: str
    status: str
    reporter_id: int
    reporter_name: str
    assignee_id: int | None
    assignee_name: str | None
    version: int
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class IssueListResponse(BaseModel):
    items: list[IssueResponse]
    total: int
    page: int
    page_size: int
