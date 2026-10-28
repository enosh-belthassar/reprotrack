"""FastAPI application entrypoint for ReproTrack."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.exceptions import ReproTrackException
from backend.app.core.logging import logger, setup_logging
from backend.app.core.request_context import get_request_id, set_request_id
from backend.app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(level="DEBUG" if settings.APP_ENV == "development" else "INFO")
    logger.info("Starting ReproTrack Backend in environment: %s", settings.APP_ENV)
    yield
    # Shutdown
    logger.info("Shutting down ReproTrack Backend...")
    engine.dispose()


app = FastAPI(
    title="ReproTrack API",
    description="Bug Reporting, Software Testing, and Fix Verification Platform API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
)


# Request ID, Timing & Security Headers Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = f"req-{uuid.uuid4().hex[:12]}"
    set_request_id(req_id)

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"

        # Defensive Security Headers (OWASP ASVS 14.4)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        if settings.APP_ENV != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
    except Exception:
        logger.exception("Unhandled server exception during request processing")
        error_headers = {
            "X-Request-ID": req_id,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "0",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": req_id,
                }
            },
            headers=error_headers,
        )


# CORS Middleware
origins = settings.cors_origin_list
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )


# Exception Handlers
@app.exception_handler(ReproTrackException)
async def reprotrack_exception_handler(request: Request, exc: ReproTrackException):
    req_id = get_request_id()
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = get_request_id()
    # Format details safely
    formatted_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        formatted_errors.append(
            {
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "request_id": req_id,
                "details": formatted_errors,
            }
        },
        headers={"X-Request-ID": req_id},
    )


# Register v1 routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "app": "ReproTrack",
        "version": "0.1.0",
        "status": "online",
        "api_v1": "/api/v1",
    }
