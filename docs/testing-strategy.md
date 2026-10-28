# ReproTrack Testing & Security Verification Strategy

**Document Version**: 2.0.0  
**Updated**: 2026-10-28  
**Total Automated Tests**: 35 passing tests  
**Linter & Type Rules**: Ruff (`E`, `F`, `W`, `I`), Bandit (AST security scanner), Pip-Audit (CVE dependencies)  

---

## 1. Testing Architecture & Test Boundary Isolation

ReproTrack enforces strict test boundary isolation:
1. **Isolated In-Memory Test Database**: All integration and penetration tests execute against an isolated `sqlite:///:memory:` instance utilizing SQLAlchemy's `StaticPool`.
2. **Per-Function Teardown**: Each test function creates a clean schema via `Base.metadata.create_all()` and drops all tables via `Base.metadata.drop_all()` in fixture teardown.
3. **No Production Mutation**: The configured test environment points to `:memory:` and never accesses or mutates `data/reprotrack.db` or live persistent stores.
4. **Synthetic Test Identities**: Synthetic user fixtures (`admin_user`, `dev_user`, `tester_user`, `viewer_user`, `outsider_user`) with dedicated hashed test passwords are used exclusively. No production or real personal identities are present in test data.

---

## 2. Test Directory Layout

```
tests/
├── conftest.py                   # In-memory SQLite fixtures, isolated TestClient, test user accounts
├── test_auth_security.py         # 10 tests: Auth, session lifecycle, throttling, admin protection
├── test_projects_isolation.py    # 3 tests: Workspaces, memberships, last admin guard, IDOR isolation
├── test_issues_workflow.py       # 8 tests: Lifecycle transitions, separation of duties, optimistic locking, comments, wont_fix reasons, developer self-verification
├── test_master_security_audit.py # 9 tests: Security headers, mass assignment rejection, whitespace/malformed validation, session revocation on demotion, patch member, SQLi literals, RBAC negative matrix, IDOR nested routes, verification invariants
├── test_reports_diagnostics.py   # 3 tests: Safe division, metrics formulas, safe diagnostics metadata
└── test_migration_empty_db.py    # 2 tests: Alembic migration execution from empty database, model registry completeness
```

---

## 3. Test Suites & Coverage Scope

### 3.1 Master Security Audit & Penetration Regression (`test_master_security_audit.py`)
- **Defensive Headers**: Asserts presence of `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 0`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and `Content-Security-Policy`.
- **Mass Assignment Defenses**: Tests `ConfigDict(extra="forbid")` by injecting forbidden fields (`status`, `issue_key`, `reporter_id`, `is_active`) on `POST /issues`, `PATCH /issues/{id}`, `POST /projects`, and `POST /users`, verifying rejection with HTTP 422.
- **Malformed & Whitespace Validation**: Rejects whitespace-only issue titles, comments, reasons, and notes. Rejects malformed email syntax (`user@`, `@domain.com`, `notanemail`).
- **Session Revocation on Privilege Demotion**: Verifies that when an administrator demotes a user's `global_role`, all active session tokens for that user are immediately revoked.
- **Project Member Role Updates & Last Admin Guard**: Tests `PATCH /projects/{id}/members/{user_id}` and prevents demoting the last remaining Project Administrator.
- **SQL-Injection Literals**: Submits SQL-injection patterns (`' OR '1'='1`, `'; DROP TABLE; --`, `UNION SELECT`) into search parameters and proves they are treated strictly as string literals without query corruption or table loss.
- **RBAC Matrix Verification**: Proves `VIEWER` cannot report defects, alter transitions, or post comments. Proves `DEVELOPER` cannot mark defects as `WONT_FIX`.
- **Cross-Project Nested IDOR**: Proves a member of Project Alpha cannot read or mutate comments, events, or verifications of an issue belonging to Project Beta.
- **Lifecycle Invariants**: Rejects attempts to jump directly from `IN_VERIFICATION` to `CLOSED` via status update; closure is strictly restricted to passing verification.

### 3.2 Authentication & Brute-Force Throttling (`test_auth_security.py`)
- Anonymous request rejection on all protected routes (HTTP 401).
- Timing-safe authentication responses for nonexistent users and incorrect passwords.
- Database-backed throttling window (`LOGIN_WINDOW_MINUTES=15`, max 5 failures) returning HTTP 429 `LOGIN_THROTTLED`.
- Explicit logout revocation and expired session rejection.
- Deactivated user session termination and last active Global Administrator protection.

### 3.3 Tenant Isolation & Permissions (`test_projects_isolation.py`)
- Project key uniqueness (HTTP 409 `DUPLICATE_PROJECT_KEY`).
- Last Project Administrator deletion prevention (HTTP 403).
- Direct object reference prevention for non-members (HTTP 403/404).

### 3.4 Issue Workflow & Verification (`test_issues_workflow.py`)
- Server-generated sequential issue keys (`PRJ-1`, `PRJ-2`).
- Optimistic concurrency control via `version` field (HTTP 409 `CONCURRENT_MODIFICATION`).
- Separation of duties: Assigned developer or developer who marked `FIXED` cannot verify even if unassigned.
- Immutable event audit logging for comments and status transitions.

### 3.5 Reporting & Database Diagnostics (`test_reports_diagnostics.py`)
- Zero-division safety on empty datasets.
- Safe diagnostics endpoint proving zero disclosure of passwords, tokens, connection strings, or filesystem paths.

### 3.6 Migrations & Model Registry (`test_migration_empty_db.py`)
- Clean migration execution from scratch using Alembic to verify all tables and constraints.
- Complete Declarative Base model registry verification.

---

## 4. Test Execution & Verification Commands

```powershell
# 1. Run all 35 automated security and functional tests
python -m pytest -v

# 2. Run targeted security penetration regression tests
python -m pytest tests/test_master_security_audit.py -v

# 3. Static code quality and style inspection
python -m ruff check .

# 4. AST static security analysis with Bandit
python -m bandit -r backend

# 5. Dependency vulnerability scanning with pip-audit
python -m pip_audit
```
