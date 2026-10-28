# ReproTrack Security Threat Model & Risk Assessment

**Document Version**: 2.0.0  
**Assessment Standards**: OWASP ASVS 5.0.0, OWASP Top 10:2025, OWASP API Security Top 10, NIST SSDF SP 800-218  
**Last Updated**: 2026-10-28  
**Scope**: ReproTrack Backend (FastAPI), Database Engine (SQLite / PostgreSQL), and Flet UI Client  

---

## 1. Protected Information Assets

| Asset Identifier | Asset Name & Description | Criticality | Confidentiality / Integrity / Availability |
|---|---|:---:|:---:|
| **AST-01** | **User Passwords & Hashes**: Argon2id hashes, salt parameters, credentials. | Critical | Confidentiality & Integrity |
| **AST-02** | **Session Tokens & Session Records**: High-entropy opaque session tokens (256-bit), SHA-256 hashes, expiry timestamps, revocation status. | Critical | Confidentiality & Integrity |
| **AST-03** | **Identity, Roles & Memberships**: Global roles (`GLOBAL_ADMIN`, `USER`), account activation status (`is_active`), and project-level workspace memberships and roles. | Critical | Integrity & Confidentiality |
| **AST-04** | **Defect & Workspace Data**: Private projects, bug titles, descriptions, steps to reproduce, expected/actual outputs, attachments, comments, and verifications. | High | Confidentiality & Integrity |
| **AST-05** | **Issue State & Workflow Sequencing**: Status transitions, assignees, project keys, issue sequential numbering, due dates. | High | Integrity |
| **AST-06** | **Audit Trail & Event History**: Append-only `issue_events` and system `audit_events`, request correlation IDs, actor identifiers, before/after values. | High | Integrity & Non-repudiation |
| **AST-07** | **Database & Configuration Secrets**: Connection strings, environment variables, server logs, database backups. | Critical | Confidentiality & Availability |
| **AST-08** | **Analytical & Dashboard Metrics**: Status breakdown, severity counts, resolution durations, reopened bug ratios, backlog aging. | Medium | Integrity |

---

## 2. Trust Boundaries

```
[Untrusted Client Context]
       │
       ▼  Boundary 1: Network & Protocol (TLS / HTTP / Reverse Proxy)
[FastAPI Gateway / Middleware]
       │  (Request ID, Defensive Security Headers, CORS, Rate Throttling)
       ▼  Boundary 2: Authentication (Bearer Token Validation & Session Expiry)
[Authenticated Request Context]
       │  Boundary 3: Global Authorization (Global Admin vs Standard User)
       ▼  Boundary 4: Workspace Isolation (Project Member vs Non-Member / IDOR)
[Project Scope Context]
       │  Boundary 5: Fine-Grained RBAC & Separation of Duties (Admin, Dev, Tester, Reporter, Viewer)
       ▼  Boundary 6: Schema & Domain Validation (Pydantic extra=forbid, State Machine Graph)
[Service Layer & Transaction Boundary]
       │  Boundary 7: Data Storage & Persistence (SQLAlchemy Parameterized Queries, PRAGMA Foreign Keys)
[Database Engine: SQLite (Local) / PostgreSQL (Production)]
       │
       ▼  Boundary 8: System Host & Database Administrator Boundary
```

### Boundary Definitions & Invariants
1. **Flet Client vs FastAPI Service**: The client is treated as untrusted. No UI validation, disabled buttons, or client-side checks are authoritative. All security controls are enforced on the backend.
2. **Anonymous vs Authenticated Caller**: All API endpoints (except `/api/v1/auth/login`, `/api/v1/system/health`, and OpenAPI documentation in dev mode) strictly require a valid, unexpired, non-revoked opaque session token.
3. **Global Role Boundary**: Global administration (`/api/v1/users`, `/api/v1/users/audit-log`) requires `GLOBAL_ADMIN` role. Standard users cannot elevate their role or view user management.
4. **Tenant / Project Isolation Boundary**: Projects are isolated workspaces. A member of Project A cannot view, report, comment on, or verify issues in Project B. Non-members receive HTTP 403 or 404 (concealing private data existence).
5. **Client-Submitted Fields vs Server-Authoritative Fields**: Clients cannot submit `issue_key`, `reporter_id`, `created_at`, `status`, or `closed_at` through create or patch requests. All mutation schemas forbid extra fields (`ConfigDict(extra="forbid")`).
6. **Separation of Duties Boundary**: A developer who implemented a fix (or was assigned when fixed) cannot verify their own fix (`POST /issues/{id}/verify` returns HTTP 403 `VERIFICATION_NOT_ALLOWED`).
7. **Application Layer vs Host/DB Operator Boundary**: Application-level append-only tables (`issue_events`, `audit_events`) protect against malicious or accidental user tampering via API endpoints. **They do NOT guarantee immutability against a database administrator, host root compromise, or direct SQLite file access.**

---

## 3. Threat Scenarios & Risk Treatment Matrix

| Threat Scenario | Attacker Profile | Likelihood | Impact | Existing Controls | Mitigations & Implemented Defenses | Residual Risk & Follow-up |
|---|---|:---:|:---:|---|---|---|
| **TS-01: Credential Brute-Force & Account Lockout** | Unauthenticated remote attacker | High | High | Generic error messages (`401 INVALID_CREDENTIALS`). Timing dummy hash on unknown users. | Database-backed throttling window (`LOGIN_WINDOW_MINUTES=15`, max 5 failures). IP-aware login attempt logging. | Highly distributed botnet attacks require external WAF/Cloudflare rate limiting. |
| **TS-02: Session Hijacking & Stale Privilege Abuse** | Malicious authenticated user or eavesdropper | Medium | Critical | High-entropy 256-bit tokens (`secrets.token_urlsafe(32)`). Tokens hashed at rest with SHA-256. | Immediate revocation on logout, account deactivation, and role demotion (`update_user`). HSTS header in non-dev. | Unencrypted HTTP local networks can expose tokens if deployed without TLS reverse proxy. |
| **TS-03: Cross-Project IDOR / BOLA** | Authenticated malicious project member | High | Critical | `ensure_project_access` check on every endpoint reading or mutating project objects. | Service-level project isolation for issues, comments, activity events, and verification runs. | Object-level caching must not bypass tenancy boundaries. |
| **TS-04: Separation of Duties Bypass (Developer Self-Verification)** | Malicious or hurried developer | High | High | `validate_fix_verification_tester` checks `issue.assignee_id != tester.id`. | Historical event scan verifies the actor who marked the issue `FIXED` cannot verify even if unassigned. | Global Admin override remains permitted and is audited in event history. |
| **TS-05: Workflow State Machine Tampering** | Authenticated user via direct API calls | High | High | Status changes routed through `transition_issue_status`. | Strict directed graph enforcement. Invariant: `IN_VERIFICATION` cannot jump to `CLOSED` except via `/verify`. | None at application boundary; transitions strictly enforced. |
| **TS-06: Mass Assignment of Server Fields** | Low-privilege authenticated user | Medium | High | Pydantic response models. | Strict `ConfigDict(extra="forbid")` on all mutation schemas. Rejects unexpected fields with HTTP 422. | Schema evolution must maintain `extra="forbid"`. |
| **TS-07: SQL Injection & ORM Escapes** | Authenticated caller submitting malicious input | Low | Critical | SQLAlchemy ORM queries with parameterized variables. | Zero raw SQL string interpolation. Safe allowlists for sorting columns and pagination boundaries. | Third-party extensions or raw text expressions must be prohibited in future PRs. |
| **TS-08: Last Administrator Lockout** | Careless or rogue administrator | Medium | High | `count_active_admins` safety check. | `LastAdminProtectionException` prevents deactivating or demoting the final active global administrator. | Requires out-of-band CLI `bootstrap-admin` if database is manually edited. |
| **TS-09: Sensitive Information Leakage in Logs/Diagnostics** | Unprivileged authenticated user | Medium | Medium | Redacting logger masks credentials and tokens. | Safe `/system/diagnostics` schema exposes only high-level runtime metadata without DB paths or secrets. | Server console output must be secured by host permissions. |
| **TS-10: Database Host Tampering** | Host operator or root compromise | Low | Critical | Application-level append-only events. | Application controls cannot prevent direct SQLite file writes by root. | Documented limitation: requires external write-once remote logging (e.g. CloudWatch, GCP Cloud Logging) in production. |

---

## 4. Attacker Profiles & Scenarios

1. **Careless Internal User**: Accidental misconfiguration, entering whitespace in titles/reasons, attempting invalid transitions.
   - *Mitigation*: Schema validation, non-empty whitespace validators, and strict state machine graphs reject invalid inputs gracefully.
2. **Malicious Authenticated Project Member**: Attempts to read or tamper with issues in another tenant/project by guessing sequential keys or IDs (IDOR).
   - *Mitigation*: Service-level `ensure_project_access` validates project membership before data serialization or mutation.
3. **Compromised Low-Privilege Account (Viewer/Reporter)**: Attacker attempts to change issue status, assign developers, or verify bugs.
   - *Mitigation*: Fine-grained RBAC enforces `require_project_role` on every state-changing route.
4. **Rogue Developer**: Attempts to verify and close their own bugs without independent QA testing.
   - *Mitigation*: Backend enforces separation of duties across assignee and historical event logs.
5. **Unauthenticated External Attacker**: Attempts password spraying, SQL injection, parameter pollution, or clickjacking.
   - *Mitigation*: Database-backed login throttling, parameterized queries, and ASVS defensive security headers (`nosniff`, `DENY`, `0`, `CSP`).
