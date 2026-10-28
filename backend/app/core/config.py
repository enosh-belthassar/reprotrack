"""Central configuration module for ReproTrack using pure Pydantic and os.environ."""

import os

from pydantic import BaseModel, Field, field_validator


def load_env_file(filepath: str = ".env") -> None:
    """Load key-value pairs from a .env file into os.environ if not already set."""
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v


# Load .env if present
load_env_file(".env")


class Settings(BaseModel):
    APP_ENV: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "development"),
        description="Application environment: development, test, staging, production",
    )
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/reprotrack.db"),
        description="SQLAlchemy database URL",
    )
    TOKEN_TTL_HOURS: int = Field(
        default_factory=lambda: int(os.getenv("TOKEN_TTL_HOURS", "8")),
        ge=1,
        le=720,
        description="Session token TTL in hours (1-720)",
    )
    CORS_ORIGINS: str = Field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:8550,http://127.0.0.1:8550"
        ),
        description="Comma-separated exact allowed browser origins",
    )
    LOGIN_WINDOW_MINUTES: int = Field(
        default_factory=lambda: int(os.getenv("LOGIN_WINDOW_MINUTES", "15")),
        ge=1,
        le=1440,
        description="Login failure counting window in minutes",
    )
    LOGIN_MAX_FAILURES: int = Field(
        default_factory=lambda: int(os.getenv("LOGIN_MAX_FAILURES", "5")),
        ge=1,
        le=100,
        description="Maximum failed attempts before throttling",
    )
    MAX_PAGE_SIZE: int = Field(
        default_factory=lambda: int(os.getenv("MAX_PAGE_SIZE", "100")),
        ge=1,
        le=500,
        description="Server-enforced upper bound for pagination",
    )
    REPROTRACK_API_URL: str = Field(
        default_factory=lambda: os.getenv("REPROTRACK_API_URL", "http://127.0.0.1:8000"),
        description="Frontend-only API base URL",
    )

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid_envs = {"development", "test", "staging", "production"}
        v_clean = v.strip().lower()
        if v_clean not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}, got '{v}'")
        return v_clean

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.CORS_ORIGINS:
            return []
        origins = [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        if self.APP_ENV == "production" and "*" in origins:
            raise ValueError("Wildcard CORS origins are forbidden in production.")
        return origins

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
