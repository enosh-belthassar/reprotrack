"""Authentication request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1, max_length=255, description="Email or username")
    password: str = Field(..., min_length=1, max_length=128, description="Password")

    @field_validator("identifier")
    @classmethod
    def validate_identifier_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Identifier cannot be blank or whitespace-only.")
        return v.strip()


class UserSummary(BaseModel):
    id: int
    display_name: str
    email_normalized: str
    global_role: str
    is_active: bool


class LoginResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_at: datetime
    user: UserSummary
