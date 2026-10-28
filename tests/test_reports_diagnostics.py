"""Reporting metrics computation and safe system diagnostics tests."""

from tests.conftest import auth_headers, get_auth_token


def test_empty_reports_metrics_safe_division(client, admin_user, test_project):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # Resolution time with 0 issues should return 0.0 without ZeroDivisionError
    res_time = client.get(
        f"/api/v1/reports/resolution-time?project_id={test_project.id}", headers=headers
    )
    assert res_time.status_code == 200
    assert res_time.json()["average_hours"] == 0.0
    assert res_time.json()["resolved_count"] == 0

    # Reopened rate with 0 runs should return 0.0 without ZeroDivisionError
    reopened = client.get(
        f"/api/v1/reports/reopened-rate?project_id={test_project.id}", headers=headers
    )
    assert reopened.status_code == 200
    assert reopened.json()["reopened_rate_percentage"] == 0.0
    assert reopened.json()["total_verified_count"] == 0

    # Backlog age
    backlog = client.get(
        f"/api/v1/reports/backlog-age?project_id={test_project.id}", headers=headers
    )
    assert backlog.status_code == 200
    assert backlog.json()["total_open"] == 0


def test_safe_diagnostics_no_secret_leakage(client, admin_user):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    diag_res = client.get("/api/v1/system/diagnostics", headers=headers)
    assert diag_res.status_code == 200
    diag = diag_res.json()

    # Verify expected safe fields are present
    assert "app_env" in diag
    assert "database_type" in diag
    assert "token_ttl_hours" in diag

    # Verify no secret or credential fields are disclosed
    diag_str = str(diag).lower()
    assert "password" not in diag_str
    assert "secret" not in diag_str
    assert "sqlite:///" not in diag_str  # No raw connection string with filesystem path
    assert "bearer" not in diag_str


def test_dashboard_summary_and_recent_activity(client, admin_user, test_project):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    summary_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "accessible_projects_count" in summary
    assert "open_issues_count" in summary
    assert "critical_high_count" in summary

    act_res = client.get("/api/v1/dashboard/recent-activity", headers=headers)
    assert act_res.status_code == 200
    assert isinstance(act_res.json(), list)
