"""Issue lifecycle, state transition contract, optimistic concurrency, and fix verification tests."""

from tests.conftest import auth_headers, get_auth_token


def test_issue_creation_and_key_sequencing(client, admin_user, test_project):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # Create first issue
    res1 = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Buffer overflow in request parser",
            "description": "Long payload crashes process",
            "steps_to_reproduce": "Send 64KB body",
            "expected_result": "Payload rejected with 413",
            "actual_result": "Process segfaults",
            "severity": "CRITICAL",
            "priority": "URGENT",
        },
        headers=headers,
    )
    assert res1.status_code == 201
    issue1 = res1.json()
    assert issue1["issue_key"] == "PRJ-1"
    assert issue1["status"] == "REPORTED"
    assert issue1["version"] == 1

    # Create second issue
    res2 = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Minor typo in navigation bar",
            "description": "Dashboard spelled Dashbord",
            "steps_to_reproduce": "Look at header",
            "expected_result": "Dashboard",
            "actual_result": "Dashbord",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    )
    assert res2.status_code == 201
    issue2 = res2.json()
    assert issue2["issue_key"] == "PRJ-2"


def test_full_lifecycle_and_verification_pass(
    client, admin_user, dev_user, tester_user, test_project
):
    dev_token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")
    tester_token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")

    # 1. Tester reports issue
    create_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Crash on empty JSON payload",
            "description": "Null pointer when parsing empty object",
            "steps_to_reproduce": "POST empty body",
            "expected_result": "422 Unprocessable Entity",
            "actual_result": "500 Internal Server Error",
            "severity": "HIGH",
            "priority": "HIGH",
        },
        headers=auth_headers(tester_token),
    )
    assert create_res.status_code == 201
    issue = create_res.json()
    issue_id = issue["id"]
    version = issue["version"]

    # 2. Triage issue: REPORTED -> TRIAGED
    triage_res = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={
            "new_status": "TRIAGED",
            "version": version,
        },
        headers=auth_headers(tester_token),
    )
    assert triage_res.status_code == 200
    issue = triage_res.json()
    assert issue["status"] == "TRIAGED"
    version = issue["version"]

    # 3. Assign to developer
    assign_res = client.post(
        f"/api/v1/issues/{issue_id}/assign",
        json={
            "assignee_id": dev_user.id,
            "version": version,
        },
        headers=auth_headers(tester_token),
    )
    assert assign_res.status_code == 200
    issue = assign_res.json()
    assert issue["assignee_id"] == dev_user.id
    version = issue["version"]

    # 4. Move to IN_PROGRESS: TRIAGED -> IN_PROGRESS
    prog_res = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={
            "new_status": "IN_PROGRESS",
            "version": version,
        },
        headers=auth_headers(dev_token),
    )
    assert prog_res.status_code == 200
    issue = prog_res.json()
    assert issue["status"] == "IN_PROGRESS"
    version = issue["version"]

    # 5. Developer completes fix: IN_PROGRESS -> FIXED
    fixed_res = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={
            "new_status": "FIXED",
            "version": version,
        },
        headers=auth_headers(dev_token),
    )
    assert fixed_res.status_code == 200
    issue = fixed_res.json()
    assert issue["status"] == "FIXED"
    version = issue["version"]

    # 6. Separation of duties check: Developer cannot verify their own fix!
    dev_verify_attempt = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        json={
            "result": "PASS",
            "test_notes": "Self verification attempt should fail",
            "tested_version": "v1.0.0",
        },
        headers=auth_headers(dev_token),
    )
    assert dev_verify_attempt.status_code == 403
    assert dev_verify_attempt.json()["error"]["code"] == "VERIFICATION_NOT_ALLOWED"

    # 7. Move to IN_VERIFICATION: FIXED -> IN_VERIFICATION
    in_verif_res = client.post(
        f"/api/v1/issues/{issue_id}/transition",
        json={
            "new_status": "IN_VERIFICATION",
            "version": version,
        },
        headers=auth_headers(tester_token),
    )
    assert in_verif_res.status_code == 200
    issue = in_verif_res.json()
    assert issue["status"] == "IN_VERIFICATION"

    # 8. Permitted tester performs PASS verification -> CLOSED
    verify_res = client.post(
        f"/api/v1/issues/{issue_id}/verify",
        json={
            "result": "PASS",
            "test_notes": "Tested in staging with 100 iterations of empty payload. Correctly returns 422.",
            "tested_version": "v1.0.1-rc2",
        },
        headers=auth_headers(tester_token),
    )
    assert verify_res.status_code == 201
    assert verify_res.json()["result"] == "PASS"

    # Verify issue is now CLOSED and closed_at is populated
    final_issue = client.get(
        f"/api/v1/issues/{issue_id}", headers=auth_headers(tester_token)
    ).json()
    assert final_issue["status"] == "CLOSED"
    assert final_issue["closed_at"] is not None


def test_verification_fail_reopens_issue(client, dev_user, tester_user, test_project):
    tester_token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    dev_token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")

    # Create and advance issue to FIXED
    c_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Memory leak on continuous polling",
            "description": "App leaks 10MB per minute",
            "steps_to_reproduce": "Run continuous poll",
            "expected_result": "Constant memory",
            "actual_result": "Memory grows indefinitely",
            "severity": "CRITICAL",
            "priority": "HIGH",
        },
        headers=auth_headers(tester_token),
    ).json()

    v = c_res["version"]
    # Triage
    t_res = client.post(
        f"/api/v1/issues/{c_res['id']}/transition",
        json={"new_status": "TRIAGED", "version": v},
        headers=auth_headers(tester_token),
    ).json()
    # In Progress
    p_res = client.post(
        f"/api/v1/issues/{c_res['id']}/transition",
        json={"new_status": "IN_PROGRESS", "version": t_res["version"]},
        headers=auth_headers(tester_token),
    ).json()
    # Fixed (performed by developer role)
    f_res = client.post(
        f"/api/v1/issues/{c_res['id']}/transition",
        json={"new_status": "FIXED", "version": p_res["version"]},
        headers=auth_headers(dev_token),
    ).json()
    assert f_res["status"] == "FIXED"

    # Tester runs FAIL verification
    fail_verify_res = client.post(
        f"/api/v1/issues/{c_res['id']}/verify",
        json={
            "result": "FAIL",
            "test_notes": "Memory leak still reproduces in v1.0.2 under load.",
            "tested_version": "v1.0.2",
        },
        headers=auth_headers(tester_token),
    )
    assert fail_verify_res.status_code == 201
    assert fail_verify_res.json()["result"] == "FAIL"

    # Status should now be REOPENED
    reopened_issue = client.get(
        f"/api/v1/issues/{c_res['id']}", headers=auth_headers(tester_token)
    ).json()
    assert reopened_issue["status"] == "REOPENED"

    # Event history contains VERIFICATION_FAILED
    events = client.get(
        f"/api/v1/issues/{c_res['id']}/events", headers=auth_headers(tester_token)
    ).json()
    event_types = [e["event_type"] for e in events]
    assert "VERIFICATION_FAILED" in event_types


def test_invalid_status_transition_rejected(client, tester_user, test_project):
    token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    headers = auth_headers(token)

    # Create issue in REPORTED status
    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Transition matrix test",
            "description": "Testing illegal leap",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    ).json()

    # Illegal direct jump: REPORTED -> CLOSED directly (without triage, fix, or verification)
    illegal_res = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={
            "new_status": "CLOSED",
            "version": res["version"],
        },
        headers=headers,
    )
    assert illegal_res.status_code == 409
    assert illegal_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_optimistic_concurrency_conflict(client, tester_user, test_project):
    token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    headers = auth_headers(token)

    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Optimistic concurrency test",
            "description": "Version testing",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    ).json()

    # Try updating with stale version (e.g., 99 instead of current version)
    stale_res = client.patch(
        f"/api/v1/issues/{res['id']}",
        json={
            "title": "Conflicting update",
            "version": 99,
        },
        headers=headers,
    )
    assert stale_res.status_code == 409
    assert stale_res.json()["error"]["code"] == "CONCURRENT_MODIFICATION"


def test_comments_and_audit_events_history(client, tester_user, test_project):
    token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    headers = auth_headers(token)

    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Comments test",
            "description": "Testing comment additions",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    ).json()

    # Add comment
    c_res = client.post(
        f"/api/v1/issues/{res['id']}/comments",
        json={
            "body": "Additional log file attached in ticket notes.",
        },
        headers=headers,
    )
    assert c_res.status_code == 201

    # List comments
    comments = client.get(f"/api/v1/issues/{res['id']}/comments", headers=headers).json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Additional log file attached in ticket notes."

    # Events history has CREATED and COMMENT_ADDED
    events = client.get(f"/api/v1/issues/{res['id']}/events", headers=headers).json()
    types = [e["event_type"] for e in events]
    assert "CREATED" in types
    assert "COMMENT_ADDED" in types


def test_wont_fix_and_reopen_transitions_require_reasons(
    client, tester_user, dev_user, test_project
):
    tester_token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    headers = auth_headers(tester_token)

    # 1. Create issue
    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Reason requirement test",
            "description": "Testing mandatory reasons",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    ).json()

    # 2. Triage
    t_res = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "TRIAGED", "version": res["version"]},
        headers=headers,
    ).json()

    # 3. Mark WONT_FIX without reason -> rejected with 422
    wont_fix_no_reason = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "WONT_FIX", "version": t_res["version"]},
        headers=headers,
    )
    assert wont_fix_no_reason.status_code == 422

    # 4. Mark WONT_FIX with reason -> accepted
    wont_fix_ok = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={
            "new_status": "WONT_FIX",
            "version": t_res["version"],
            "reason": "Intended behavior as per PRD spec section 4",
        },
        headers=headers,
    )
    assert wont_fix_ok.status_code == 200
    wf_issue = wont_fix_ok.json()
    assert wf_issue["status"] == "WONT_FIX"

    # 5. Move WONT_FIX -> TRIAGED without reason -> rejected with 422
    retriage_no_reason = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "TRIAGED", "version": wf_issue["version"]},
        headers=headers,
    )
    assert retriage_no_reason.status_code == 422

    # 6. Move WONT_FIX -> TRIAGED with reason -> accepted
    retriage_ok = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={
            "new_status": "TRIAGED",
            "version": wf_issue["version"],
            "reason": "New business requirements necessitate this change",
        },
        headers=headers,
    )
    assert retriage_ok.status_code == 200
    assert retriage_ok.json()["status"] == "TRIAGED"


def test_fixing_developer_cannot_verify_fix_even_if_unassigned(
    client, tester_user, dev_user, test_project
):
    tester_token = get_auth_token(client, "tester@reprotrack.test", "TesterSecurePass123!")
    dev_token = get_auth_token(client, "dev@reprotrack.test", "DevSecurePass123!")

    # 1. Create issue
    res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Fixing developer unassignment loophole test",
            "description": "Developer fixes then unassigns to bypass check",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "MEDIUM",
            "priority": "HIGH",
        },
        headers=auth_headers(tester_token),
    ).json()

    # 2. Triage & In Progress
    t = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "TRIAGED", "version": res["version"]},
        headers=auth_headers(tester_token),
    ).json()

    p = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "IN_PROGRESS", "version": t["version"]},
        headers=auth_headers(dev_token),
    ).json()

    # 3. Developer transitions to FIXED
    f = client.post(
        f"/api/v1/issues/{res['id']}/transition",
        json={"new_status": "FIXED", "version": p["version"]},
        headers=auth_headers(dev_token),
    ).json()

    # 4. Unassign developer from issue
    unassign = client.post(
        f"/api/v1/issues/{res['id']}/assign",
        json={"assignee_id": None, "version": f["version"]},
        headers=auth_headers(tester_token),
    ).json()
    assert unassign["assignee_id"] is None

    # 5. Developer attempts to verify fix -> MUST BE REJECTED 403
    dev_verify = client.post(
        f"/api/v1/issues/{res['id']}/verify",
        json={
            "result": "PASS",
            "test_notes": "Attempting to verify after unassigning myself",
            "tested_version": "v1.2.0",
        },
        headers=auth_headers(dev_token),
    )
    assert dev_verify.status_code == 403
    assert dev_verify.json()["error"]["code"] == "VERIFICATION_NOT_ALLOWED"
