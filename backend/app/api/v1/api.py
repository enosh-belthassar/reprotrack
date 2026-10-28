"""Main API router combining all v1 endpoints."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    auth,
    dashboard,
    issues,
    projects,
    reports,
    system,
    users,
    verification,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(issues.router)
api_router.include_router(verification.router)
api_router.include_router(reports.router)
api_router.include_router(users.router)
api_router.include_router(system.router)
