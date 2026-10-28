"""Master Security Audit & Penetration Regression Test Suite for ReproTrack.

Covers:
- OWASP ASVS Defensive Security Response Headers
- Mass Assignment (extra=forbid) Rejection on All Mutation Schemas
- Whitespace-only / Malformed Input Rejection (titles, reasons, notes, emails)
- Demotion / Role Escalation Session Revocation
- Project Member Role Update and Last Admin Protection
- Safe SQL-Injection-shaped Character Handling
- Exhaustive Role-Based Access Control (RBAC) & IDOR Matrix
- Invariant & Lifecycle State Transition Bypasses
"""

from backend.app.core.permissions import GlobalRole, ProjectRole
from backend.app.core.security import hash_password
from backend.app.models.issue import Issue
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User
from tests.conftest import auth_headers, get_auth_token


def test_defensive_security_response_headers(client, admin_user):
    """Verify standard OWASP defensive headers are present on API responses."""
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    res = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "0"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


def test_mass_assignment_extra_fields_rejected(client, admin_user, test_project):
    """Verify that unexpected fields in request bodies are rejected with 422."""
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # 1. Attempt mass assignment on IssueCreate (injecting status and issue_key)
    res_create = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Legitimate Title",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
            "status": "CLOSED",  # Malicious injection
            "issue_key": "FORGED-99",  # Malicious injection
        },
        headers=headers,
    )
    assert res_create.status_code == 422
    err_body = res_create.json()["error"]
    assert err_body["code"] == "VALIDATION_ERROR"

    # Create a legitimate issue for patch testing
    legit_issue_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Valid Issue Title",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=headers,
    )
    assert legit_issue_res.status_code == 201
    issue_id = legit_issue_res.json()["id"]

    # 2. Attempt mass assignment on IssueUpdate (injecting status, reporter_id, etc.)
    res_patch = client.patch(
        f"/api/v1/issues/{issue_id}",
        json={
            "version": 1,
            "status": "CLOSED",  # Malicious injection
            "reporter_id": 999,  # Malicious injection
        },
        headers=headers,
    )
    assert res_patch.status_code == 422

    # 3. Attempt mass assignment on ProjectCreate
    res_proj = client.post(
        "/api/v1/projects",
        json={
            "key": "SEC",
            "name": "Security Project",
            "is_active": False,  # Malicious injection
            "next_issue_number": 500,  # Malicious injection
        },
        headers=headers,
    )
    assert res_proj.status_code == 422

    # 4. Attempt mass assignment on UserCreate
    res_user = client.post(
        "/api/v1/users",
        json={
            "display_name": "Test User",
            "email": "valid@reprotrack.test",
            "password": "ValidPassword123!",
            "is_active": False,  # Malicious injection
        },
        headers=headers,
    )
    assert res_user.status_code == 422


def test_input_validation_whitespace_and_malformed_syntax(client, admin_user, test_project):
    """Verify that whitespace-only fields and malformed email syntax are rejected."""
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # 1. Whitespace-only issue title
    res_title = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "     ",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=headers,
    )
    assert res_title.status_code == 422

    # 2. Malformed email address in UserCreate
    for malformed_email in ["notanemail", "user@", "@domain.com", "user@domain"]:
        res_email = client.post(
            "/api/v1/users",
            json={
                "display_name": "Invalid Email User",
                "email": malformed_email,
                "password": "ValidPassword123!",
            },
            headers=headers,
        )
        assert res_email.status_code == 422, f"Expected 422 for malformed email '{malformed_email}'"

    # Create legitimate issue
    issue_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Issue for Validation",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=headers,
    )
    issue_id = issue_res.json()["id"]

    # 3. Whitespace-only comment body
    res_comment = client.post(
        f"/api/v1/issues/{issue_id}/comments",
        json={"body": "    \n   "},
        headers=headers,
    )
    assert res_comment.status_code == 422

    # 4. Whitespace-only transition reason when moving to WONT_FIX
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "TRIAGED", "version": 1},
        headers=headers,
    )
    res_wontfix = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "WONT_FIX", "version": 2, "reason": "   "},
        headers=headers,
    )
    assert res_wontfix.status_code == 422

    # 5. Whitespace-only verification notes and tested version
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "TRIAGED", "version": 2, "reason": "Valid reason"},
        headers=headers,
    )
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "IN_PROGRESS", "version": 3},
        headers=headers,
    )
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "FIXED", "version": 4},
        headers=headers,
    )

    res_verif_notes = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        json={"result": "PASS", "test_notes": "   ", "tested_version": "v1.0.0"},
        headers=headers,
    )
    assert res_verif_notes.status_code == 422

    res_verif_ver = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        json={"result": "PASS", "test_notes": "Valid test notes", "tested_version": "   "},
        headers=headers,
    )
    assert res_verif_ver.status_code == 422


def test_user_demotion_revokes_active_sessions(client, db, admin_user):
    """Verify that when a user's global_role is altered, active sessions are revoked."""
    # Create a secondary admin
    sub_admin = User(
        display_name="Secondary Admin",
        email_normalized="subadmin@reprotrack.test",
        password_hash=hash_password("SubAdminPass123!"),
        global_role=GlobalRole.GLOBAL_ADMIN,
        is_active=True,
    )
    db.add(sub_admin)
    db.commit()

    # Log in as sub_admin
    sub_admin_token = get_auth_token(client, "subadmin@reprotrack.test", "SubAdminPass123!")
    sub_admin_headers = auth_headers(sub_admin_token)

    # Confirm token is currently valid
    check_res = client.get("/api/v1/auth/me", headers=sub_admin_headers)
    assert check_res.status_code == 200

    # Primary admin demotes sub_admin to standard USER
    primary_admin_token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    demote_res = client.patch(
        f"/api/v1/users/{sub_admin.id}",
        json={"global_role": "USER"},
        headers=auth_headers(primary_admin_token),
    )
    assert demote_res.status_code == 200
    assert demote_res.json()["global_role"] == "USER"

    # Previous session token must now be rejected
    rejected_res = client.get("/api/v1/auth/me", headers=sub_admin_headers)
    assert rejected_res.status_code == 401
    assert rejected_res.json()["error"]["code"] == "UNAUTHORIZED"


def test_project_member_role_update_and_last_admin_demotion(
    client, db, admin_user, dev_user, test_project
):
    """Verify PATCH member role and that last Project Administrator cannot be demoted."""
    admin_token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(admin_token)

    # 1. Update developer to tester
    update_res = client.patch(
        f"/api/v1/projects/{test_project.id}/members/{dev_user.id}",
        json={"role": "TESTER"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["role"] == "TESTER"

    # 2. Attempt to demote the only PROJECT_ADMIN
    demote_admin_res = client.patch(
        f"/api/v1/projects/{test_project.id}/members/{admin_user.id}",
        json={"role": "DEVELOPER"},
        headers=headers,
    )
    assert demote_admin_res.status_code == 403
    assert (
        "Cannot demote the last Project Administrator"
        in demote_admin_res.json()["error"]["message"]
    )


def test_sql_injection_shaped_inputs_safely_handled(client, admin_user, test_project):
    """Verify SQL-injection patterns are treated strictly as literals."""
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # Search with SQL injection patterns
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE issues; --",
        "UNION SELECT NULL, NULL, NULL--",
        "1' AND sleep(1)--",
    ]
    for payload in sqli_payloads:
        res = client.get(
            f"/api/v1/issues?project_id={test_project.id}&search={payload}",
            headers=headers,
        )
        assert res.status_code == 200
        # No issues should match this literal string
        assert res.json()["total"] == 0

    # Verify database is intact
    check_res = client.get("/api/v1/system/health")
    assert check_res.status_code == 200
    assert check_res.json()["database_connected"] is True


def test_comprehensive_role_based_access_control(client, db, test_project, viewer_user, dev_user):
    """Test RBAC negative operations across roles."""
    viewer_token = get_auth_token(client, "viewer@reprotrack.test", "ViewerSecurePass123!")
    viewer_headers = auth_headers(viewer_token)

    dev_token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")
    dev_headers = auth_headers(dev_token)

    # 1. VIEWER cannot report an issue
    res_viewer_report = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Viewer Defect",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=viewer_headers,
    )
    assert res_viewer_report.status_code == 403

    # Developer creates an issue
    dev_create_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Developer Issue",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=dev_headers,
    )
    assert dev_create_res.status_code == 201
    issue_id = dev_create_res.json()["id"]

    # 2. VIEWER cannot transition issue
    res_viewer_trans = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "TRIAGED", "version": 1},
        headers=viewer_headers,
    )
    assert res_viewer_trans.status_code == 403

    # 3. VIEWER cannot add comments (read-only observer)
    res_viewer_comm = client.post(
        f"/api/v1/issues/{issue_id}/comments",
        json={"body": "Viewer comment"},
        headers=viewer_headers,
    )
    assert res_viewer_comm.status_code == 403

    # 4. DEVELOPER cannot mark issue as WONT_FIX (only Admin or Tester can mark WONT_FIX)
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "TRIAGED", "version": 1},
        headers=dev_headers,
    )
    dev_wontfix = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "WONT_FIX", "version": 2, "reason": "Developer trying wont_fix"},
        headers=dev_headers,
    )
    assert dev_wontfix.status_code == 403


def test_cross_project_nested_idor_prevention(client, db, admin_user, test_project):
    """Test that a member of Project Alpha cannot access comments, events, or verifications of Project Beta."""
    # Create Project Beta
    proj_beta = Project(
        key="BETA",
        name="Beta Project",
        description="Isolated Beta Project",
        created_by_id=admin_user.id,
        next_issue_number=1,
    )
    db.add(proj_beta)
    db.flush()

    # Create Beta issue
    beta_issue = Issue(
        issue_key="BETA-1",
        project_id=proj_beta.id,
        title="Beta Secret Issue",
        description="Private information",
        steps_to_reproduce="Steps",
        expected_result="Expected",
        actual_result="Actual",
        status="REPORTED",
        reporter_id=admin_user.id,
        version=1,
    )
    db.add(beta_issue)
    db.commit()
    db.refresh(beta_issue)

    # Create user who is only a member of Project Alpha (test_project)
    alpha_member = User(
        display_name="Alpha Only Member",
        email_normalized="alphaonly@reprotrack.test",
        password_hash=hash_password("AlphaPass123!"),
        global_role=GlobalRole.USER,
        is_active=True,
    )
    db.add(alpha_member)
    db.flush()
    db.add(
        ProjectMember(
            project_id=test_project.id,
            user_id=alpha_member.id,
            role=ProjectRole.DEVELOPER,
        )
    )
    db.commit()

    alpha_token = get_auth_token(client, "alphaonly@reprotrack.test", "AlphaPass123!")
    headers = auth_headers(alpha_token)

    # 1. Attempt to read Beta issue
    res_read = client.get(f"/api/v1/issues/{beta_issue.id}", headers=headers)
    assert res_read.status_code in {403, 404}

    # 2. Attempt to read Beta issue comments
    res_comments = client.get(f"/api/v1/issues/{beta_issue.id}/comments", headers=headers)
    assert res_comments.status_code in {403, 404}

    # 3. Attempt to read Beta issue events
    res_events = client.get(f"/api/v1/issues/{beta_issue.id}/events", headers=headers)
    assert res_events.status_code in {403, 404}

    # 4. Attempt to read Beta issue verifications
    res_verifs = client.get(f"/api/v1/issues/{beta_issue.id}/verifications", headers=headers)
    assert res_verifs.status_code in {403, 404}

    # 5. Attempt to post comment on Beta issue
    res_post_comm = client.post(
        f"/api/v1/issues/{beta_issue.id}/comments",
        json={"body": "Intruder comment"},
        headers=headers,
    )
    assert res_post_comm.status_code in {403, 404}

    # 6. Attempt to verify Beta issue
    res_verify = client.post(
        f"/api/v1/issues/{beta_issue.id}/verify",
        json={"result": "PASS", "test_notes": "Intruder verification", "tested_version": "v1.0"},
        headers=headers,
    )
    assert res_verify.status_code in {403, 404}


def test_in_verification_cannot_transition_directly_to_closed(
    client, admin_user, tester_user, test_project
):
    """Verify invariant: IN_VERIFICATION cannot transition to CLOSED via status transition endpoint."""
    admin_token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(admin_token)

    # Create issue and move through to IN_VERIFICATION
    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Verification Bypass Target",
            "description": "Details",
            "steps_to_reproduce": "Steps",
            "expected_result": "Expected",
            "actual_result": "Actual",
        },
        headers=headers,
    )
    issue_id = res.json()["id"]

    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "TRIAGED", "version": 1},
        headers=headers,
    )
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "IN_PROGRESS", "version": 2},
        headers=headers,
    )
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "FIXED", "version": 3},
        headers=headers,
    )
    client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "IN_VERIFICATION", "version": 4},
        headers=headers,
    )

    # Attempt to jump directly to CLOSED via transition endpoint
    bypass_res = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={"new_status": "CLOSED", "version": 5},
        headers=headers,
    )
    assert bypass_res.status_code == 409
    assert bypass_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
