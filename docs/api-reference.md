# ReproTrack API Reference (v1)

Base URL: `http://127.0.0.1:8000/api/v1`

---

## 1. Defensive Security Headers & Standard Envelope

Every HTTP response from the ReproTrack backend includes standard defensive security headers:
- `X-Request-ID`: Unique correlation identifier for tracing.
- `X-Response-Time-Ms`: Server execution latency in milliseconds.
- `X-Content-Type-Options`: `nosniff`
- `X-Frame-Options`: `DENY`
- `X-XSS-Protection`: `0`
- `Referrer-Policy`: `strict-origin-when-cross-origin`
- `Permissions-Policy`: `geolocation=(), camera=(), microphone=()`
- `Content-Security-Policy`: `default-src 'self'`

### Error Response Envelope
All error responses adhere to a uniform JSON envelope:
```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Transition from REPORTED to CLOSED is not allowed.",
    "request_id": "req-9a3b4c12df8e",
    "details": null
  }
}
```

### Stable Error Codes
| Code | HTTP Status | Description |
|---|:---:|---|
| `UNAUTHORIZED` | 401 | Missing, invalid, expired, or revoked bearer session token |
| `INVALID_CREDENTIALS` | 401 | Generic authentication error (timing-safe; does not disclose account existence) |
| `FORBIDDEN` | 403 | Insufficient global or project-level role permissions |
| `USER_INACTIVE` | 403 | Deactivated account attempting access |
| `VERIFICATION_NOT_ALLOWED`| 403 | Separation of duties violation (developer self-verification denial) |
| `PROJECT_ACCESS_DENIED` | 403 | User is not a member of the project workspace |
| `PROJECT_NOT_FOUND` | 404 | Project does not exist or access is forbidden |
| `ISSUE_NOT_FOUND` | 404 | Defect does not exist or belongs to another project |
| `DUPLICATE_PROJECT_KEY` | 409 | Project key already allocated |
| `DUPLICATE_ISSUE_KEY` | 409 | Issue key sequence conflict |
| `INVALID_STATUS_TRANSITION`| 409 | Disallowed state transition attempt along lifecycle graph |
| `CONCURRENT_MODIFICATION` | 409 | Optimistic locking version conflict |
| `LAST_ADMIN_PROTECTION` | 409 | Cannot demote or deactivate the last active administrator |
| `VALIDATION_ERROR` | 422 | Schema validation failure (bad enum, string length, whitespace, unexpected fields) |
| `LOGIN_THROTTLED` | 429 | Exceeded maximum failed login attempts within window |

---

## 2. Authentication Endpoints

### `POST /auth/login`
Authenticate using email and password. Returns opaque session bearer token.
- **Request Body**: `{"identifier": "...", "password": "..."}`
- **Security Protections**: Database-backed throttling window, timing dummy hash on unknown users, password max length bounds (128 chars).
- **Response**: 200 OK `{"token": "...", "token_type": "Bearer", "expires_at": "...", "user": {...}}`

### `POST /auth/logout`
Revoke the current opaque session token immediately in the database.
- **Headers**: `Authorization: Bearer <token>`
- **Response**: 200 OK `{"message": "Successfully logged out."}`

### `GET /auth/me`
Retrieve profile of currently authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response**: 200 OK `{"id": 1, "display_name": "...", "email_normalized": "...", "global_role": "...", "is_active": true}`

---

## 3. Projects & Workspaces

### `GET /projects`
List all active projects accessible to current user (Global Admin sees all; standard users see memberships).
- **Response**: 200 OK `List[ProjectResponse]`

### `POST /projects`
Create a new project workspace. (Creator is automatically assigned `PROJECT_ADMIN`).
- **Request Body**: `{"key": "RT", "name": "ReproTrack Core", "description": "..."}`
- **Response**: 201 Created `ProjectResponse`

### `GET /projects/{project_id}`
Retrieve project details, issue count (bounded count query), and current user's role.
- **Response**: 200 OK `ProjectResponse`

### `PATCH /projects/{project_id}`
Update project name, description, or active status (`PROJECT_ADMIN` or `GLOBAL_ADMIN` only).
- **Response**: 200 OK `ProjectResponse`

### `GET /projects/{project_id}/members`
List team members in project workspace.
- **Response**: 200 OK `List[ProjectMemberResponse]`

### `POST /projects/{project_id}/members`
Add a user to the project with an assigned role (`PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `REPORTER`, `VIEWER`).
- **Response**: 201 Created `ProjectMemberResponse`

### `PATCH /projects/{project_id}/members/{user_id}`
Update a project member's role (`PROJECT_ADMIN` or `GLOBAL_ADMIN` only). Protects the last remaining `PROJECT_ADMIN` from demotion.
- **Request Body**: `{"role": "TESTER"}`
- **Response**: 200 OK `ProjectMemberResponse`

### `DELETE /projects/{project_id}/members/{user_id}`
Remove user from project. Prevents removing the last remaining `PROJECT_ADMIN`.
- **Response**: 204 No Content

---

## 4. Defects & Lifecycle Workflow

### `GET /issues`
Multi-dimensional issue listing with pagination and filtering.
- **Query Parameters**:
  - `project_id`: Optional[int]
  - `status`: Optional[str]
  - `severity`: Optional[str]
  - `priority`: Optional[str]
  - `assignee_id`: Optional[int]
  - `search`: Optional[str] (treated strictly as literal data)
  - `page`: int (default 1)
  - `page_size`: int (default 25, capped by MAX_PAGE_SIZE)
  - `sort_by`: str (default "created_at", allowlisted)
  - `sort_dir`: str (default "desc")
- **Response**: 200 OK `{"items": [...], "total": 42, "page": 1, "page_size": 25}`

### `POST /issues`
Report a new bug with server-generated unique issue key.
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "title": "Null pointer on empty payload",
    "description": "Details...",
    "steps_to_reproduce": "1. Send empty body",
    "expected_result": "422 Error",
    "actual_result": "500 Error",
    "environment": "Chrome 122",
    "severity": "HIGH",
    "priority": "HIGH"
  }
  ```
- **Response**: 201 Created `IssueResponse`

### `GET /issues/{issue_id}`
Retrieve issue details including reproduction steps and expected/actual outcomes.
- **Response**: 200 OK `IssueResponse`

### `PATCH /issues/{issue_id}`
Update issue metadata. Requires optimistic concurrency control `version`. Rejects extra fields (`status`, `reporter_id`, etc.) with HTTP 422.
- **Request Body**: `{"title": "Updated Title", "version": 2}`
- **Response**: 200 OK `IssueResponse`

### `POST /issues/{issue_id}/assign`
Assign or unassign a defect to a developer. Requires `version`.
- **Request Body**: `{"assignee_id": 3, "version": 2}`
- **Response**: 200 OK `IssueResponse`

### `POST /issues/{issue_id}/transition`
Execute an atomic status transition along the verified lifecycle graph.
- **Request Body**: `{"new_status": "FIXED", "version": 3, "reason": "Optional reason"}`
- **Response**: 200 OK `IssueResponse`

### `GET /issues/{issue_id}/comments` / `POST /issues/{issue_id}/comments`
Read discussion notes or append an immutable investigation comment (`VIEWER` role excluded from posting).
- **POST Request**: `{"body": "Investigated root cause in line 42."}`
- **Response**: 201 Created `IssueCommentResponse`

### `GET /issues/{issue_id}/events`
Read append-only event history and state transition audit logs for this issue.
- **Response**: 200 OK `List[IssueEventResponse]`

---

## 5. Fix Verification Console

### `GET /verification/pending`
Retrieve all issues currently in `FIXED` or `IN_VERIFICATION` status across accessible projects.
- **Response**: 200 OK `List[IssueResponse]`

### `POST /issues/{issue_id}/verify` (or `POST /verification/{issue_id}`)
Record a formal QA verification run with tested build tag and notes.
- **Rules**:
  - `PASS`: Atomically transitions status to `CLOSED`, records `closed_at`, logs `VERIFICATION_PASSED`.
  - `FAIL`: Atomically transitions status to `REOPENED`, clears `resolved_at`, logs `VERIFICATION_FAILED` and preserves test notes.
  - **Separation of Duties**: Rejects request with 403 `VERIFICATION_NOT_ALLOWED` if actor is the assignee or was the developer who marked the issue `FIXED`.
- **Request Body**: `{"result": "PASS", "test_notes": "100 iterations tested.", "tested_version": "v1.0.4-rc2"}`
- **Response**: 201 Created `VerificationResponse`

---

## 6. Analytical Reports & Dashboard

- `GET /dashboard/summary`: High-level defect metrics across user's accessible projects.
- `GET /dashboard/recent-activity`: Recent defect activity stream scoped to accessible projects.
- `GET /reports/status-breakdown`: Defect distribution by status.
- `GET /reports/severity-breakdown`: Defect distribution by severity.
- `GET /reports/resolution-time`: Average hours, median hours, resolved counts (timezone normalized).
- `GET /reports/reopened-rate`: Total verified runs, failed runs, reopen rate percentage.
- `GET /reports/backlog-age`: Aging breakdown (under 7 days, 7-30 days, over 30 days, total open).

---

## 7. User Administration & Safe Diagnostics

- `GET /users`: List all platform accounts (`GLOBAL_ADMIN` only).
- `POST /users`: Provision user account with normalized email syntax (`GLOBAL_ADMIN` only).
- `PATCH /users/{id}`: Update name or global role. Demoting an admin or altering role immediately invalidates their active sessions (`GLOBAL_ADMIN` only; protects last admin).
- `POST /users/{id}/deactivate`: Soft-deactivate user and terminate active sessions immediately (`GLOBAL_ADMIN` only; protects last admin).
- `GET /users/audit-log`: List platform administrative audit trail (`GLOBAL_ADMIN` only).
- `GET /system/health`: Live health status and database ping check (unauthenticated).
- `GET /system/diagnostics`: Safe configuration metadata without secret or filesystem disclosure.
