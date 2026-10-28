# ReproTrack

> **Secure Bug Reporting, Issue Workflow & Fix Verification Platform**

ReproTrack is a software defect management and verification platform engineered for software teams, QA leads, and student software projects. It delivers an auditable bug resolution lifecycle with backend-enforced state transitions, separation of duties, and verification metrics.

---

## Key Features

- **Enforced Lifecycle State Machine**:
  `REPORTED -> TRIAGED -> IN_PROGRESS -> FIXED -> IN_VERIFICATION -> CLOSED`
  Invalid transitions are rejected by the server with HTTP 409 (`INVALID_STATUS_TRANSITION`).
- **Separation of Duties**:
  A developer marking an issue as `FIXED` cannot verify their own fix. QA sign-off requires a permitted tester or administrator role.
- **Dedicated Fix Verification Console**:
  Formal verification station recording tested build/version tags, verification notes, and PASS (to `CLOSED`) or FAIL (to `REOPENED`) outcomes.
- **Two-Tier Role-Based Access Control**:
  Global Roles (`GLOBAL_ADMIN`, `USER`) and Workspace Project Roles (`PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `REPORTER`, `VIEWER`).
- **Tenant Workspace Isolation**:
  Defects, memberships, and comments are isolated per project to prevent IDOR / BOLA vulnerabilities.
- **Optimistic Concurrency Control (OCC)**:
  `version` lock checks on defect mutations prevent lost updates.
- **Database-Backed Throttling & Session Security**:
  Argon2id password hashing, database-backed brute force throttling (HTTP 429), and 256-bit opaque bearer session tokens.
- **Comprehensive Quality Reports**:
  Database-derived metrics: defect counts by status and severity, mean/median resolution time, reopen rate %, and backlog age health.
- **Technical Precision UI**:
  Modular Flet client crafted with deep-navy (`#15263B`) and action-mint (`#36B78A`) tokens following modern enterprise data density standards.

---

## Architecture & Technology Stack

- **Backend**: Python 3.12, FastAPI 0.142+, Uvicorn, Pydantic v2
- **Database ORM**: SQLAlchemy 2.1+, Alembic 1.20+ (SQLite local default, PostgreSQL ready)
- **Frontend**: Python Flet 1.0.5 (Desktop & Web responsive UI)
- **Security**: Argon2id via `argon2-cffi`
- **Testing**: Pytest, Starlette TestClient, Ruff linter/formatter

---

## Quick Start Guide

### 1. Installation
Clone the repository and install dependencies in your Python virtual environment:
```bash
python -m pip install -e ".[dev]"
```

### 2. Database Migrations
Initialize the database tables using Alembic:
```bash
python -m backend.app.cli migrate
```

### 3. Administrator Bootstrap
Create the initial Global Administrator account (prompts are masked securely; no default credentials exist):
```bash
python -m backend.app.cli bootstrap-admin
```

### 4. (Optional) Seed Demo Dataset
To populate sample projects, test tickets, and verification runs for local evaluation:
```bash
python -m backend.app.cli seed-demo
```

### 5. Launch Services

**Start the FastAPI Backend Service:**
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be accessible at: `http://127.0.0.1:8000/docs`

**Start the Flet Frontend Application:**
In a separate terminal:
```bash
python -m frontend.main
```

---

## Quality & Security Verification

Execute the complete automated test suite (35 comprehensive tests):
```bash
python -m pytest tests -v
```

Execute code linting and formatting validation with Ruff:
```bash
python -m ruff check backend tests frontend
```

Execute AST security analysis with Bandit:
```bash
python -m bandit -r backend
```

---

## Detailed Documentation

Comprehensive technical specifications are available in [`docs/`](docs/):
- [Architecture & Boundaries](docs/architecture.md)
- [Database Schema & Constraints](docs/database-design.md)
- [API Reference (v1)](docs/api-reference.md)
- [Permissions & Role Matrix](docs/permissions.md)
- [Security Threat Model](docs/security-threat-model.md)
- [Testing Strategy](docs/testing-strategy.md)
- [Deployment & Operations](docs/deployment.md)
- [Master Security Audit Report](docs/security-test-report.md)

