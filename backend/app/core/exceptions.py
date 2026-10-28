"""Centralized exceptions and error shapes for ReproTrack."""

from typing import Any

from fastapi import HTTPException

from backend.app.core.request_context import get_request_id


class ReproTrackException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": get_request_id(),
            }
        }
        if self.details:
            data["error"]["details"] = self.details
        return data


class InvalidCredentialsException(ReproTrackException):
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(status_code=401, code="INVALID_CREDENTIALS", message=message)


class LoginThrottledException(ReproTrackException):
    def __init__(self, message: str = "Too many failed login attempts. Please try again later."):
        super().__init__(status_code=429, code="LOGIN_THROTTLED", message=message)


class UserInactiveException(ReproTrackException):
    def __init__(self, message: str = "Account is inactive. Please contact your administrator."):
        super().__init__(status_code=403, code="USER_INACTIVE", message=message)


class UnauthorizedException(ReproTrackException):
    def __init__(self, message: str = "Authentication required."):
        super().__init__(
            status_code=401,
            code="UNAUTHORIZED",
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(ReproTrackException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(status_code=403, code="FORBIDDEN", message=message)


class ProjectNotFoundException(ReproTrackException):
    def __init__(self, message: str = "Project not found or inaccessible."):
        super().__init__(status_code=404, code="PROJECT_NOT_FOUND", message=message)


class ProjectAccessDeniedException(ReproTrackException):
    def __init__(self, message: str = "Access to this project is denied."):
        super().__init__(status_code=403, code="PROJECT_ACCESS_DENIED", message=message)


class IssueNotFoundException(ReproTrackException):
    def __init__(self, message: str = "Issue not found or inaccessible."):
        super().__init__(status_code=404, code="ISSUE_NOT_FOUND", message=message)


class InvalidStatusTransitionException(ReproTrackException):
    def __init__(self, message: str = "This status transition is not allowed."):
        super().__init__(status_code=409, code="INVALID_STATUS_TRANSITION", message=message)


class VerificationNotAllowedException(ReproTrackException):
    def __init__(self, message: str = "You are not authorized to verify this fix."):
        super().__init__(status_code=403, code="VERIFICATION_NOT_ALLOWED", message=message)


class DuplicateProjectKeyException(ReproTrackException):
    def __init__(self, message: str = "A project with this key already exists."):
        super().__init__(status_code=409, code="DUPLICATE_PROJECT_KEY", message=message)


class DuplicateIssueKeyException(ReproTrackException):
    def __init__(
        self,
        message: str = "A concurrency conflict occurred while assigning an issue key. Please retry.",
    ):
        super().__init__(status_code=409, code="DUPLICATE_ISSUE_KEY", message=message)


class ValidationErrorException(ReproTrackException):
    def __init__(self, message: str = "Validation failed.", details: Any | None = None):
        super().__init__(status_code=422, code="VALIDATION_ERROR", message=message, details=details)


class ConcurrentModificationException(ReproTrackException):
    def __init__(
        self, message: str = "The record was modified by another transaction. Please reload."
    ):
        super().__init__(status_code=409, code="CONCURRENT_MODIFICATION", message=message)


class LastAdminProtectionException(ReproTrackException):
    def __init__(
        self, message: str = "Cannot demote or deactivate the last active global administrator."
    ):
        super().__init__(status_code=409, code="LAST_ADMIN_PROTECTION", message=message)
