# ReproTrack Permissions & RBAC Matrix

**Document Version**: 2.0.0  
**Updated**: 2026-10-28  
**Policy Philosophy**: Default-Deny. Access is rejected unless explicit membership or administrative authority is verified.

---

## 1. Role Taxonomy

ReproTrack employs a dual-tiered authorization model:
1. **Global Platform Roles**: Control platform administration and cross-workspace visibility.
2. **Project Workspace Roles**: Control defect tracking, triage, fix delivery, and verification within individual project tenants.

### Global Roles
- `GLOBAL_ADMIN`: Super-administrator with universal oversight across all projects, access to user provisioning, and access to platform audit logs.
- `USER`: Standard platform account whose access to defect tracking is strictly bounded by active project memberships.

### Project Roles
- `PROJECT_ADMIN`: Project lead responsible for project metadata, workspace member management, defect triage, and fix verification.
- `DEVELOPER`: Software engineer permitted to report issues, start development work (`IN_PROGRESS`), and submit completed fixes (`FIXED`). Cannot verify their own fixes.
- `TESTER`: QA engineer responsible for reproducing defects, reporting issues, triaging, and executing independent fix verification runs (`PASS` or `FAIL`).
- `REPORTER`: Workspace contributor permitted to create defects, view project items, and participate in issue discussions.
- `VIEWER`: Read-only observer who can inspect issues, comments, verifications, and analytical dashboards. **Cannot mutate state or post comments.**

---

## 2. Endpoint-by-Endpoint Authorization Matrix

| Endpoint Route | HTTP Method | Anonymous? | Required Global Role | Required Project Role | Operation Summary | Result When Denied |
|---|:---:|:---:|:---:|:---:|---|:---:|
| `/api/v1/auth/login` | POST | **Yes** | Any | None | Authenticate with credentials & obtain session token | 401 `INVALID_CREDENTIALS` / 429 `LOGIN_THROTTLED` |
| `/api/v1/auth/logout` | POST | No | Any | None | Revoke session token and terminate session | 401 `UNAUTHORIZED` |
| `/api/v1/auth/me` | GET | No | Any | None | Retrieve authenticated user profile | 401 `UNAUTHORIZED` / 403 `USER_INACTIVE` |
| `/api/v1/projects` | GET | No | Any | None (scoped) | List accessible projects (Admin sees all; User sees memberships) | 401 `UNAUTHORIZED` |
| `/api/v1/projects` | POST | No | Any | None | Create new project workspace (Creator becomes `PROJECT_ADMIN`) | 401 `UNAUTHORIZED` |
| `/api/v1/projects/{id}` | GET | No | Any | Member of `{id}` or `GLOBAL_ADMIN` | Inspect workspace details and issue totals | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/projects/{id}` | PATCH | No | Any | `PROJECT_ADMIN` or `GLOBAL_ADMIN` | Update project name, description, or active status | 403 `FORBIDDEN` |
| `/api/v1/projects/{id}/members` | GET | No | Any | Member of `{id}` or `GLOBAL_ADMIN` | List workspace members and assigned roles | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/projects/{id}/members` | POST | No | Any | `PROJECT_ADMIN` or `GLOBAL_ADMIN` | Add active platform user to workspace | 403 `FORBIDDEN` |
| `/api/v1/projects/{id}/members/{user_id}` | PATCH | No | Any | `PROJECT_ADMIN` or `GLOBAL_ADMIN` | Update member role (protects last Project Admin) | 403 `FORBIDDEN` |
| `/api/v1/projects/{id}/members/{user_id}` | DELETE | No | Any | `PROJECT_ADMIN` or `GLOBAL_ADMIN` | Remove member from workspace (protects last Project Admin) | 403 `FORBIDDEN` |
| `/api/v1/issues` | GET | No | Any | Member of `{id}` or `GLOBAL_ADMIN` | Query issues with pagination, search, and sorting | 403 `PROJECT_ACCESS_DENIED` |
| `/api/v1/issues` | POST | No | Any | `PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `REPORTER`, or `GLOBAL_ADMIN` | Report new defect with server-sequenced issue key | 403 `FORBIDDEN` |
| `/api/v1/issues/{id}` | GET | No | Any | Member of issue's project or `GLOBAL_ADMIN` | Retrieve defect details and reproduction steps | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/issues/{id}` | PATCH | No | Any | Triage role if severity/priority modified | Update issue metadata with optimistic concurrency | 403 `FORBIDDEN` / 409 `CONCURRENT_MODIFICATION` |
| `/api/v1/issues/{id}/assign` | POST | No | Any | `PROJECT_ADMIN`, `TESTER`, `DEVELOPER`, or `GLOBAL_ADMIN` | Assign or unassign defect to a developer | 403 `FORBIDDEN` |
| `/api/v1/issues/{id}/transition` | POST | No | Any | Role dependent on transition graph | Transition defect along verified lifecycle graph | 403 `FORBIDDEN` / 409 `INVALID_STATUS_TRANSITION` |
| `/api/v1/issues/{id}/comments` | GET | No | Any | Member of issue's project or `GLOBAL_ADMIN` | Read discussion notes for defect | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/issues/{id}/comments` | POST | No | Any | `PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `REPORTER`, or `GLOBAL_ADMIN` | Append discussion comment (VIEWER excluded) | 403 `FORBIDDEN` |
| `/api/v1/issues/{id}/events` | GET | No | Any | Member of issue's project or `GLOBAL_ADMIN` | Inspect append-only event trail for defect | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/issues/{id}/verifications`| GET | No | Any | Member of issue's project or `GLOBAL_ADMIN` | List fix verification records | 403 `PROJECT_ACCESS_DENIED` / 404 |
| `/api/v1/issues/{id}/verify` | POST | No | Any | `PROJECT_ADMIN`, `TESTER`, or `GLOBAL_ADMIN` | Record fix verification (`PASS` -> `CLOSED`, `FAIL` -> `REOPENED`) | 403 `VERIFICATION_NOT_ALLOWED` / 409 |
| `/api/v1/verification/pending` | GET | No | Any | None (scoped to memberships) | Retrieve `FIXED` and `IN_VERIFICATION` issues awaiting testing | 401 `UNAUTHORIZED` |
| `/api/v1/reports/*` | GET | No | Any | Member of specified project or `GLOBAL_ADMIN` | Analytical dashboards and metrics (status, severity, SLA, etc.) | 403 `PROJECT_ACCESS_DENIED` |
| `/api/v1/dashboard/*` | GET | No | Any | None (scoped to memberships) | High-level summary metrics across user's projects | 401 `UNAUTHORIZED` |
| `/api/v1/users` | GET | No | `GLOBAL_ADMIN` | None | List all platform accounts | 403 `FORBIDDEN` |
| `/api/v1/users` | POST | No | `GLOBAL_ADMIN` | None | Provision new platform account | 403 `FORBIDDEN` |
| `/api/v1/users/{id}` | PATCH | No | `GLOBAL_ADMIN` | None | Update user display name or global role | 403 `FORBIDDEN` / 409 `LAST_ADMIN_PROTECTION` |
| `/api/v1/users/{id}/deactivate` | POST | No | `GLOBAL_ADMIN` | None | Deactivate account and terminate active sessions | 403 `FORBIDDEN` / 409 `LAST_ADMIN_PROTECTION` |
| `/api/v1/users/audit-log` | GET | No | `GLOBAL_ADMIN` | None | View platform administrative audit trail | 403 `FORBIDDEN` |
| `/api/v1/system/health` | GET | **Yes** | Any | None | Service liveness and database ping check | 200 OK / Degraded |
| `/api/v1/system/diagnostics` | GET | No | Any | None | Safe system configuration and limits | 401 `UNAUTHORIZED` |

---

## 3. Workflow State Transition Matrix & Permitted Roles

The issue lifecycle state machine enforces both graph adjacency and role authority:

```
                  +-----------------------------------+
                  |                                   |
                  v                                   |
[REPORTED] ---> [TRIAGED] ---> [IN_PROGRESS] ---> [FIXED]
                  |                                   |
                  |                                   v
                  |                           [IN_VERIFICATION]
                  |                               /        \
                  |                     PASS     /          \ FAIL
                  |                             v            v
                  +---> [WONT_FIX]          [CLOSED]      [REOPENED]
                           |                   |               |
                           +--- Re-triage -----+               |
                                                               v
                                                      [IN_PROGRESS]
```

| Source State | Target State | Permitted Roles | Invariants & Business Logic |
|---|---|---|---|
| `REPORTED` | `TRIAGED` | `PROJECT_ADMIN`, `TESTER`, `DEVELOPER`, `GLOBAL_ADMIN` | Verifies and prioritizes defect. |
| `TRIAGED` | `IN_PROGRESS` | `PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `GLOBAL_ADMIN` | Developer begins implementation. |
| `TRIAGED` | `WONT_FIX` | `PROJECT_ADMIN`, `TESTER`, `GLOBAL_ADMIN` | **Requires non-empty `reason`**. Developers cannot mark WONT_FIX. |
| `WONT_FIX` | `TRIAGED` | `PROJECT_ADMIN`, `TESTER`, `DEVELOPER`, `GLOBAL_ADMIN` | **Requires non-empty `reason`**. |
| `IN_PROGRESS` | `FIXED` | `PROJECT_ADMIN`, `DEVELOPER`, `GLOBAL_ADMIN` | Fix is delivered and ready for testing. Sets `resolved_at`. |
| `FIXED` | `IN_VERIFICATION` | `PROJECT_ADMIN`, `TESTER`, `GLOBAL_ADMIN` | QA begins test execution. |
| `FIXED` / `IN_VERIFICATION` | `CLOSED` | `PROJECT_ADMIN`, `TESTER`, `GLOBAL_ADMIN` | **Cannot be set via transition API!** Closed ONLY via `/verify` with `result: PASS`. **Separation of Duties**: Developer cannot verify their own fix. |
| `FIXED` / `IN_VERIFICATION` | `REOPENED` | `PROJECT_ADMIN`, `TESTER`, `GLOBAL_ADMIN` | Triggered via `/verify` with `result: FAIL`. Preserves test notes and tested version in immutable audit trail. |
| `CLOSED` | `REOPENED` | `PROJECT_ADMIN`, `TESTER`, `GLOBAL_ADMIN` | **Requires non-empty `reason`**. |
| `REOPENED` | `IN_PROGRESS` | `PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `GLOBAL_ADMIN` | Developer addresses failed verification. |

---

## 4. Separation of Duties Policy (Anti-Self-Verification)

- **Rule**: A developer cannot verify or close an issue they implemented or were assigned to.
- **Enforcement Mechanism**:
  1. If `issue.assignee_id == tester.id`, verification is rejected with 403 `VERIFICATION_NOT_ALLOWED`.
  2. The system inspects historical `issue_events`. If the caller was the actor who transitioned the issue to `FIXED`, verification is rejected even if the issue was unassigned or reassigned.
  3. `GLOBAL_ADMIN` possesses emergency administrative override privileges, which are visibly logged in the audit event stream.
