"""User management schemas."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    global_role: str = Field(default="USER", pattern="^(GLOBAL_ADMIN|USER)$")

    @field_validator("email")
    @classmethod
    def validate_email_syntax(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return clean

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Display name cannot be whitespace-only.")
        return clean


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(None, min_length=2, max_length=100)
    global_role: str | None = Field(None, pattern="^(GLOBAL_ADMIN|USER)$")

    @field_validator("display_name")
    @classmethod
    def validate_display_name_optional(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 2:
                raise ValueError("Display name cannot be whitespace-only.")
            return clean
        return None


class UserResponse(BaseModel):
    id: int
    display_name: str
    email_normalized: str
    global_role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
