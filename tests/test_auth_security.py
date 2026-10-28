"""Authentication, session lifecycle, rate limiting, and security tests."""

from datetime import timedelta

from backend.app.core.db_utils import utc_now
from backend.app.models.user import SessionModel
from tests.conftest import auth_headers, get_auth_token


def test_unauthenticated_request_rejected(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    data = res.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_login_successful_and_me_profile(client, dev_user):
    res = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "dev@reprotrack.test",
            "password": "DevSecurePass123!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email_normalized"] == "dev@reprotrack.test"
    assert data["user"]["display_name"] == "Jane Developer"

    token = data["token"]
    me_res = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me_res.status_code == 200
    assert me_res.json()["id"] == dev_user.id


def test_login_invalid_password_returns_generic_error(client, dev_user):
    res = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "dev@reprotrack.test",
            "password": "WrongPassword999!",
        },
    )
    assert res.status_code == 401
    data = res.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert "Invalid email or password" in data["error"]["message"]


def test_login_nonexistent_user_returns_same_generic_error(client):
    res = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "nonexistent@reprotrack.test",
            "password": "SomeRandomPassword123!",
        },
    )
    assert res.status_code == 401
    data = res.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert "Invalid email or password" in data["error"]["message"]


def test_login_throttling_after_max_failures(client, dev_user):
    # Attempt 5 failed logins (configured MAX_FAILURES is 5)
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "dev@reprotrack.test",
                "password": "BadPassword!",
            },
        )

    # The 6th attempt should be throttled (HTTP 429)
    res = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "dev@reprotrack.test",
            "password": "DevSecurePass123!",
        },
    )
    assert res.status_code == 429
    data = res.json()
    assert data["error"]["code"] == "LOGIN_THROTTLED"


def test_logout_invalidates_session(client, dev_user):
    token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")
    headers = auth_headers(token)

    # Confirm token works
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Confirm token is now rejected
    post_logout = client.get("/api/v1/auth/me", headers=headers)
    assert post_logout.status_code == 401
    assert post_logout.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_session_rejected(client, db, dev_user):
    token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")
    headers = auth_headers(token)

    # Manually backdate the session expiration in the database
    session_row = db.query(SessionModel).filter(SessionModel.user_id == dev_user.id).first()
    session_row.expires_at = utc_now() - timedelta(hours=1)
    db.commit()

    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_deactivated_user_cannot_access_or_login(client, db, admin_user, dev_user):
    admin_token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    dev_token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")

    # Deactivate dev_user via administrative API
    deact_res = client.post(
        f"/api/v1/users/{dev_user.id}/deactivate",
        headers=auth_headers(admin_token),
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # Old session token is now rejected
    old_session_res = client.get("/api/v1/auth/me", headers=auth_headers(dev_token))
    assert old_session_res.status_code in {401, 403}

    # New login attempt is rejected
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "dev@reprotrack.test",
            "password": "DevSecurePass123!",
        },
    )
    assert login_res.status_code == 403
    assert login_res.json()["error"]["code"] == "USER_INACTIVE"


def test_last_active_admin_protection(client, admin_user):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # Attempt to deactivate the only active admin
    res = client.post(f"/api/v1/users/{admin_user.id}/deactivate", headers=headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "LAST_ADMIN_PROTECTION"

    # Attempt to demote the only active admin
    demote_res = client.patch(
        f"/api/v1/users/{admin_user.id}",
        json={"global_role": "USER"},
        headers=headers,
    )
    assert demote_res.status_code == 409
    assert demote_res.json()["error"]["code"] == "LAST_ADMIN_PROTECTION"


def test_non_admin_cannot_access_user_management(client, dev_user):
    token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")
    res = client.get("/api/v1/users", headers=auth_headers(token))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
