"""Database and datetime utilities."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)
