"""Structured, redacted logging for ReproTrack."""

import logging
import re

from backend.app.core.request_context import get_request_id

REDACT_PATTERNS = [
    (re.compile(r'(password["\':\s=]+)([\w!@#$%^&*()-+=~`]+)', re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'(token["\':\s=]+)([\w\-._~+/]+=*)', re.IGNORECASE), r"\1[REDACTED]"),
    (
        re.compile(r'(authorization["\':\s=]+Bearer\s+)([\w\-._~+/]+=*)', re.IGNORECASE),
        r"\1[REDACTED]",
    ),
    (re.compile(r"(gho_[a-zA-Z0-9]{36})", re.IGNORECASE), r"[REDACTED]"),
]


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        req_id = get_request_id()
        if req_id and f"[{req_id}]" not in formatted:
            formatted = f"[{req_id}] {formatted}"
        for pattern, replacement in REDACT_PATTERNS:
            formatted = pattern.sub(replacement, formatted)
        return formatted


def setup_logging(level: str = "INFO") -> None:
    logger = logging.getLogger("reprotrack")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False


logger = logging.getLogger("reprotrack")
