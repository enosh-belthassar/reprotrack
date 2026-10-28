# ReproTrack Database Design & Data Integrity

## 1. Schema Overview & Relational Model
The ReproTrack relational schema enforces data integrity, foreign key cascades, tenant isolation, and auditability.

```
 [users] 1 --- * [sessions]
    |    1 --- * [login_attempts] (by normalized email)
    |    1 --- * [project_members] * --- 1 [projects]
    |                                          |
    |                                          1
    |                                          |
    +----------- 1 --- * [issues] * -----------+
                           |
                           +--- 1 --- * [issue_comments]
                           |
                           +--- 1 --- * [issue_events] (immutable)
                           |
                           +--- 1 --- * [verification_runs] (immutable)
```

## 2. Table Specifications

### 2.1 `users`
- `id`: Integer, Primary Key, Auto-increment.
- `display_name`: String(100), NOT NULL.
- `email_normalized`: String(255), UNIQUE, Indexed, NOT NULL. Stored in lowercase to prevent case-variation collisions.
- `password_hash`: String(255), NOT NULL. Argon2id salt and digest string.
- `global_role`: String(50), NOT NULL (`GLOBAL_ADMIN` or `USER`).
- `is_active`: Boolean, default `True`, NOT NULL. Soft-deactivation preserves audit and event history.
- `created_at`, `updated_at`: DateTime(timezone=True), UTC timestamps.
- `last_login_at`: DateTime(timezone=True), nullable.

### 2.2 `sessions`
- `id`: Integer, Primary Key.
- `user_id`: Integer, Foreign Key -> `users.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `token_hash`: String(64), UNIQUE, Indexed, NOT NULL. SHA-256 digest of opaque bearer token.
- `created_at`, `expires_at`: DateTime(timezone=True), Indexed, NOT NULL.
- `revoked_at`: DateTime(timezone=True), Indexed, Nullable. Explicit logout populates revocation timestamp.
- `user_agent`: String(255), Nullable client metadata.

### 2.3 `login_attempts`
- `id`: Integer, Primary Key.
- `identifier`: String(255), Indexed, NOT NULL (normalized login email).
- `timestamp`: DateTime(timezone=True), Indexed, NOT NULL.
- `result`: String(20), NOT NULL (`SUCCESS` or `FAILED`).
- `ip_address`: String(50), Nullable client IP.
- Compound Index: `ix_login_attempts_ident_time` on `(identifier, timestamp)` for sub-millisecond throttle evaluations.

### 2.4 `projects`
- `id`: Integer, Primary Key.
- `key`: String(10), UNIQUE, Indexed, NOT NULL. Short uppercase prefix (e.g., `RT`, `ALPHA`).
- `name`: String(100), NOT NULL.
- `description`: Text, default `""`, NOT NULL.
- `is_active`: Boolean, default `True`, NOT NULL.
- `created_by_id`: Integer, Foreign Key -> `users.id`, NOT NULL.
- `next_issue_number`: Integer, default `1`, NOT NULL. Concurrency-safe sequence counter for keys like `RT-101`.
- `created_at`, `updated_at`: DateTime(timezone=True), NOT NULL.

### 2.5 `project_members`
- `id`: Integer, Primary Key.
- `project_id`: Integer, Foreign Key -> `projects.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `user_id`: Integer, Foreign Key -> `users.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `role`: String(50), NOT NULL (`PROJECT_ADMIN`, `DEVELOPER`, `TESTER`, `REPORTER`, `VIEWER`).
- `created_at`: DateTime(timezone=True), NOT NULL.
- Unique Constraint: `uq_project_member` on `(project_id, user_id)`.

### 2.6 `issues`
- `id`: Integer, Primary Key, Indexed.
- `issue_key`: String(20), UNIQUE, Indexed, NOT NULL (e.g., `RT-101`).
- `project_id`: Integer, Foreign Key -> `projects.id` (ON DELETE RESTRICT), Indexed, NOT NULL.
- `title`: String(255), NOT NULL.
- `description`: Text, NOT NULL.
- `steps_to_reproduce`: Text, NOT NULL.
- `expected_result`: Text, NOT NULL.
- `actual_result`: Text, NOT NULL.
- `environment`: String(255), Nullable.
- `severity`: String(20), Indexed, NOT NULL (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `priority`: String(20), Indexed, NOT NULL (`LOW`, `NORMAL`, `HIGH`, `URGENT`).
- `status`: String(30), Indexed, NOT NULL (`REPORTED`, `TRIAGED`, `IN_PROGRESS`, `FIXED`, `IN_VERIFICATION`, `CLOSED`, `REOPENED`, `WONT_FIX`).
- `reporter_id`: Integer, Foreign Key -> `users.id`, Indexed, NOT NULL.
- `assignee_id`: Integer, Foreign Key -> `users.id`, Indexed, Nullable.
- `version`: Integer, default `1`, NOT NULL. Optimistic concurrency control lock.
- `due_at`: DateTime(timezone=True), Nullable.
- `created_at`, `updated_at`: DateTime(timezone=True), NOT NULL.
- `resolved_at`: DateTime(timezone=True), Nullable (set on `FIXED`).
- `closed_at`: DateTime(timezone=True), Nullable (set on passing verification to `CLOSED`).
- Compound Indexes: `(project_id, status)`, `(project_id, severity)`.

### 2.7 `issue_comments`
- `id`: Integer, Primary Key.
- `issue_id`: Integer, Foreign Key -> `issues.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `author_id`: Integer, Foreign Key -> `users.id`, NOT NULL.
- `body`: Text, NOT NULL.
- `created_at`: DateTime(timezone=True), NOT NULL.

### 2.8 `issue_events` (Immutable Audit Trail)
- `id`: Integer, Primary Key.
- `issue_id`: Integer, Foreign Key -> `issues.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `actor_id`: Integer, Foreign Key -> `users.id`, Nullable.
- `event_type`: String(50), NOT NULL (`CREATED`, `STATUS_CHANGED`, `ASSIGNED`, `METADATA_UPDATED`, `COMMENT_ADDED`, `VERIFICATION_PASSED`, `VERIFICATION_FAILED`).
- `old_value`, `new_value`: String(100), Nullable.
- `details`: Text, Nullable (JSON or description).
- `request_id`: String(64), Nullable (tracing correlation ID).
- `created_at`: DateTime(timezone=True), NOT NULL.

### 2.9 `verification_runs` (Immutable Quality Records)
- `id`: Integer, Primary Key.
- `issue_id`: Integer, Foreign Key -> `issues.id` (ON DELETE CASCADE), Indexed, NOT NULL.
- `tester_id`: Integer, Foreign Key -> `users.id`, Indexed, NOT NULL.
- `result`: String(10), NOT NULL (`PASS` or `FAIL`).
- `test_notes`: Text, NOT NULL.
- `tested_version`: String(50), NOT NULL (e.g., `v1.2.0-rc1`).
- `created_at`: DateTime(timezone=True), NOT NULL.

### 2.10 `audit_events` (Administrative System Audit)
- `id`: Integer, Primary Key.
- `actor_id`: Integer, Foreign Key -> `users.id` (ON DELETE SET NULL), Indexed, Nullable.
- `action`: String(100), Indexed, NOT NULL.
- `entity_type`: String(50), NOT NULL.
- `entity_id`: String(50), Nullable.
- `metadata_json`: Text, Nullable.
- `timestamp`: DateTime(timezone=True), Indexed, NOT NULL.
- `request_id`: String(64), Nullable.

## 3. SQLite and PostgreSQL Compatibility
- **PRAGMAs**: On SQLite connection events, ReproTrack activates:
  - `PRAGMA foreign_keys=ON;` to enforce foreign key constraints.
  - `PRAGMA journal_mode=WAL;` to enable concurrent readers and writers.
- **Batch Mode Migrations**: Alembic migrations configure `render_as_batch=True` on SQLite so table alterations work within SQLite table rebuild limitations.
