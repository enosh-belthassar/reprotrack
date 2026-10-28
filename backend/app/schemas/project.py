"""Project and membership schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(
        ...,
        min_length=2,
        max_length=10,
        pattern="^[A-Z0-9]+$",
        description="Uppercase key e.g. RT, REP",
    )
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Project name cannot be whitespace-only.")
        return clean


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=2000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name_optional(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 2:
                raise ValueError("Project name cannot be whitespace-only.")
            return clean
        return None


class ProjectMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role: str = Field(..., pattern="^(PROJECT_ADMIN|DEVELOPER|TESTER|REPORTER|VIEWER)$")


class ProjectMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., pattern="^(PROJECT_ADMIN|DEVELOPER|TESTER|REPORTER|VIEWER)$")


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user_name: str
    user_email: str
    role: str
    created_at: datetime


class ProjectResponse(BaseModel):
    id: int
    key: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    issue_count: int = 0
    my_role: str | None = None
