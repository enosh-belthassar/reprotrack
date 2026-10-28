"""Request context tracking for ReproTrack."""

import contextvars
import uuid

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current correlation ID or generate a fallback."""
    val = request_id_ctx.get()
    if not val:
        val = f"req-{uuid.uuid4().hex[:12]}"
        request_id_ctx.set(val)
    return val


def set_request_id(req_id: str) -> None:
    request_id_ctx.set(req_id)
