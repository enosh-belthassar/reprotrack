"""Project membership, authorization, and tenant isolation tests."""

from backend.app.core.permissions import GlobalRole
from backend.app.core.security import hash_password
from backend.app.models.user import User
from tests.conftest import auth_headers, get_auth_token


def test_project_creation_and_duplicate_key_rejection(client, admin_user):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # 1. Create project
    res = client.post(
        "/api/v1/projects",
        json={
            "key": "ALPHA",
            "name": "Alpha Project",
            "description": "First project",
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["key"] == "ALPHA"

    # 2. Duplicate key should be rejected with HTTP 409
    dup_res = client.post(
        "/api/v1/projects",
        json={
            "key": "ALPHA",
            "name": "Duplicate Alpha Project",
            "description": "Conflict key",
        },
        headers=headers,
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_PROJECT_KEY"


def test_project_members_crud_and_last_admin_protection(
    client, db, admin_user, dev_user, test_project
):
    token = get_auth_token(client, "admin@reprotrack.test", "AdminSecurePass123!")
    headers = auth_headers(token)

    # List members
    members_res = client.get(f"/api/v1/projects/{test_project.id}/members", headers=headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) >= 4

    # Attempt to remove the only PROJECT_ADMIN
    remove_admin_res = client.delete(
        f"/api/v1/projects/{test_project.id}/members/{admin_user.id}",
        headers=headers,
    )
    assert remove_admin_res.status_code == 403
    assert (
        "Cannot remove the last Project Administrator"
        in remove_admin_res.json()["error"]["message"]
    )

    # Remove developer member
    remove_dev_res = client.delete(
        f"/api/v1/projects/{test_project.id}/members/{dev_user.id}",
        headers=headers,
    )
    assert remove_dev_res.status_code == 204


def test_cross_project_isolation_idor_prevention(client, db, admin_user, dev_user, test_project):
    # Create an outsider user who is not a member of test_project
    outsider = User(
        display_name="External User",
        email_normalized="outsider@reprotrack.test",
        password_hash=hash_password("OutsiderPass123!"),
        global_role=GlobalRole.USER,
        is_active=True,
    )
    db.add(outsider)
    db.commit()

    outsider_token = get_auth_token(client, "outsider@reprotrack.test", "OutsiderPass123!")
    headers = auth_headers(outsider_token)

    # 1. Outsider cannot access project details
    detail_res = client.get(f"/api/v1/projects/{test_project.id}", headers=headers)
    assert detail_res.status_code in {403, 404}

    # 2. Outsider cannot list project members
    members_res = client.get(f"/api/v1/projects/{test_project.id}/members", headers=headers)
    assert members_res.status_code in {403, 404}

    # 3. Outsider cannot report an issue in this project
    create_issue_res = client.post(
        "/api/v1/issues",
        json={
            "project_id": test_project.id,
            "title": "Unauthorized Issue",
            "description": "Should fail",
            "steps_to_reproduce": "N/A",
            "expected_result": "N/A",
            "actual_result": "N/A",
            "severity": "LOW",
            "priority": "LOW",
        },
        headers=headers,
    )
    assert create_issue_res.status_code in {403, 404}
