# ReproTrack Deployment & Operations Guide

**Document Version**: 2.0.0  
**Updated**: 2026-10-28  
**Target Environments**: Development, Test, Staging, Production  

---

## 1. Environment Configuration Contract

All configuration settings are parsed, type-validated, and bounded via pure Pydantic (`backend/app/core/config.py`). Settings are populated from environment variables or a local `.env` file (see `.env.example`).

| Variable | Default Value | Valid Constraints | Description |
|---|---|---|---|
| `APP_ENV` | `development` | `development`, `test`, `staging`, `production` | Environment mode. In `production`, wildcard CORS (`*`) is strictly forbidden and documentation endpoints (`/docs`, `/redoc`) are disabled. |
| `DATABASE_URL` | `sqlite:///./data/reprotrack.db` | Valid SQLAlchemy URI | Database connection string. Supports SQLite and PostgreSQL (`postgresql+psycopg2://...`). |
| `TOKEN_TTL_HOURS` | `8` | Integer `1` to `720` | Lifetime in hours for opaque session tokens. |
| `CORS_ORIGINS` | `http://localhost:8550,http://127.0.0.1:8550` | Comma-separated list | Allowed exact browser origins. Wildcards forbidden in production. |
| `LOGIN_WINDOW_MINUTES` | `15` | Integer `1` to `1440` | Rolling window duration for tracking failed authentication attempts. |
| `LOGIN_MAX_FAILURES` | `5` | Integer `1` to `100` | Maximum failed attempts allowed before triggering database-backed throttling. |
| `MAX_PAGE_SIZE` | `100` | Integer `1` to `500` | Server-enforced maximum page size ceiling for pagination. |
| `REPROTRACK_API_URL` | `http://127.0.0.1:8000` | Valid URL | **Frontend client configuration only**. Contains no credentials or secrets. |

---

## 2. Defensive Security Response Headers (OWASP ASVS 14.4)

The backend automatically injects defensive security headers into all HTTP responses:
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing attacks.
- `X-Frame-Options: DENY`: Prevents UI redressing and clickjacking.
- `X-XSS-Protection: 0`: Disables buggy legacy browser XSS filters in favor of CSP.
- `Referrer-Policy: strict-origin-when-cross-origin`: Restricts referrer information leakage.
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`: Disables unused hardware device APIs.
- `Content-Security-Policy: default-src 'self'`: Restricts script, style, and object execution to self origin.
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`: Injected automatically in non-development environments (`APP_ENV != "development"`).

---

## 3. Production Deployment Architecture

```
[Web Browser / Desktop Clients]
               │
           HTTPS (443)
               ▼
   [Nginx / Caddy Reverse Proxy]
       - TLS Termination (Let's Encrypt / Managed Certs)
       - Strict-Transport-Security (HSTS)
       - Reverse Proxy to Uvicorn via Unix Socket or Loopback (127.0.0.1:8000)
               │
               ▼
   [Uvicorn / FastAPI Backend (Gunicorn Process Manager)]
       - Workers: (2 * CPU Cores) + 1
       - Host: 127.0.0.1 (Loopback only; never bind directly to 0.0.0.0 without a firewall)
               │
               ▼
   [Managed PostgreSQL Database]
       - Dedicated user with restricted privileges
       - SSL connection enforcement (`sslmode=require`)
```

### Production Hardening Checklist
1. **APP_ENV**: Set `APP_ENV=production`. Swagger UI and OpenAPI documentation are suppressed to prevent unauthorized reconnaissance.
2. **Database Engine**: Transition from SQLite to PostgreSQL for multi-worker concurrency and connection pooling. SQLite single-writer locking is unsuitable for horizontally scaled web instances.
3. **CORS_ORIGINS**: Supply exact origins (e.g. `https://reprotrack.yourdomain.com`). Never configure wildcard `*`.
4. **Secrets Management**: Ensure `.env` is stored securely with restricted file permissions (`chmod 600 .env`) and never committed to version control.
5. **Initial Bootstrapping**: Run `python -m backend.app.cli bootstrap-admin` interactively to create the first administrator with a secure, unique password.

---

## 4. Backup & Disaster Recovery

### PostgreSQL (Production)
Execute automated daily logical backups with point-in-time recovery (PITR) enabled:
```bash
pg_dump -U reprotrack_user -h pg-host -Fc reprotrack > /var/backups/reprotrack_$(date +%Y%m%d).dump
```

### SQLite (Local / Single Instance)
Do **not** perform raw filesystem file copies (`cp`) while the database is actively in WAL mode, as this can result in inconsistent or corrupt backup files. Use the SQLite Online Backup API:
```python
import sqlite3

src = sqlite3.connect("data/reprotrack.db")
dst = sqlite3.connect("backups/reprotrack_backup.db")
with dst:
    src.backup(dst)
src.close()
dst.close()
```
