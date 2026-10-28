# ReproTrack Architecture Specification

## 1. System Overview
ReproTrack is an enterprise-grade Bug Reporting, Software Testing, and Fix Verification Platform built for engineering teams, QA leads, and student software projects. It delivers an auditable bug resolution lifecycle with backend-enforced state transitions and separation of duties.

## 2. Component Boundaries & Request Flow
The platform is organized into three decoupled layers:

```
+-------------------------------------------------------------------------+
|                           Flet UI Client                                |
|  - Presentation Components (Badges, Cards, Split Panes, Kanban)         |
|  - Centralized Design Tokens (Technical Precision Navy & Mint)          |
|  - Session State & Auto-Logout Guard (AppState)                         |
+-------------------------------------------------------------------------+
                                    |
                        HTTP / JSON (REST API)
                                    v
+-------------------------------------------------------------------------+
|                         FastAPI Backend (/api/v1)                       |
|  - Request ID & Latency Telemetry Middleware                            |
|  - Structured Error Envelope & Exception Handlers                       |
|  - Pydantic v2 Request/Response Validation                              |
|  - Argon2id Password Hashing & High-Entropy Opaque Session Tokens       |
|  - Database-Backed Login Throttling (Rate Limiting)                     |
|  - Role-Based Access Control (RBAC) & Tenant Project Isolation          |
|  - Lifecycle Transition Engine & Optimistic Concurrency Control         |
|  - Separation of Duties (Developer Self-Verification Prevention)        |
+-------------------------------------------------------------------------+
                                    |
                           SQLAlchemy 2.x ORM
                                    v
+-------------------------------------------------------------------------+
|                  Database (SQLite Local / PostgreSQL)                   |
|  - Foreign Key Constraints & PRAGMA foreign_keys=ON                     |
|  - WAL Journaling & UTC Timestamp Normalization                         |
|  - Alembic Version-Controlled Schema Migrations                         |
|  - Atomic Change & Audit Event Persistence                              |
+-------------------------------------------------------------------------+
```

### Strict Architectural Boundaries
1. **Frontend-to-Backend Isolation**: The Flet UI client never accesses SQLAlchemy sessions or database models directly. All reads and mutations route exclusively through `ReproTrackApiClient` over HTTP to `/api/v1`.
2. **Business Services Separation**: Business services in `backend/app/services/` have zero dependencies on Flet or HTTP frameworks. They interact solely with database models, schemas, and security primitives.
3. **Thin Route Handlers**: FastAPI endpoint handlers perform dependency injection, authenticate the request context, and delegate logic to domain services.

## 3. Technology Stack & Pinned Boundaries
- **Backend**: Python 3.12+, FastAPI, Uvicorn, Pydantic v2, Pydantic Settings
- **Database ORM & Migrations**: SQLAlchemy 2.x, Alembic
- **Cryptography**: Argon2id via `argon2-cffi`
- **Frontend**: Python Flet 1.0.5 (Desktop & Web responsive layout)
- **Quality Assurance**: Pytest, HTTPX, Starlette TestClient, Ruff linter/formatter

## 4. Key Architectural Decisions (ADRs)
- **Opaque Session Tokens**: Rather than insecure client-side JWTs that cannot be revoked without state stores, ReproTrack uses high-entropy 256-bit opaque tokens. Only the SHA-256 hash is persisted in the `sessions` table.
- **Database-Backed Throttling**: Failed authentication attempts are logged in `login_attempts` with UTC timestamps. Throttling is evaluated against the database within the sliding window `LOGIN_WINDOW_MINUTES`, protecting against brute-force attacks across clustered instances.
- **Optimistic Concurrency Control (OCC)**: Every issue record maintains an integer `version` field. Modifications submit the expected version; conflicts reject concurrent mutations with HTTP 409 (`CONCURRENT_MODIFICATION`).
- **Separation of Duties**: The developer assigned to an issue cannot verify or close their own fix. Verification requires a permitted tester or administrator role.
