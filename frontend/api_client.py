"""Reusable, structured HTTP API client for ReproTrack Flet frontend."""

import os
from typing import Any, Callable, Dict, List, Optional

import httpx


class ApiClientError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
    ):
        super().__init__(f"[{status_code}] {code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class ReproTrackApiClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        on_unauthorized: Optional[Callable[[], None]] = None,
    ):
        # Resolve API base URL without trailing slash
        resolved_url = (
            base_url or os.getenv("REPROTRACK_API_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.base_url = f"{resolved_url}/api/v1"
        self.timeout = timeout
        self.on_unauthorized = on_unauthorized
        self.token: Optional[str] = None
        self._client = httpx.Client(timeout=self.timeout)

    def set_token(self, token: Optional[str]) -> None:
        self.token = token

    def clear_token(self) -> None:
        self.token = None

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response(self, response: httpx.Response) -> Any:
        # Success status
        if 200 <= response.status_code < 300:
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        # Parse error envelope
        code = "UNKNOWN_ERROR"
        message = f"Server returned error HTTP {response.status_code}"
        details = None

        try:
            body = response.json()
            if isinstance(body, dict) and "error" in body:
                err = body["error"]
                code = err.get("code", code)
                message = err.get("message", message)
                details = err.get("details", details)
            elif isinstance(body, dict) and "detail" in body:
                message = str(body["detail"])
        except Exception:
            if response.text:
                message = response.text[:200]

        # Trigger unauthorized hook on 401
        if response.status_code == 401 and self.on_unauthorized:
            self.on_unauthorized()

        raise ApiClientError(
            status_code=response.status_code,
            code=code,
            message=message,
            details=details,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            clean_params = None
            if params:
                clean_params = {k: v for k, v in params.items() if v is not None}

            response = self._client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=clean_params,
                json=json_data,
            )
            return self._handle_response(response)
        except httpx.RequestError as exc:
            raise ApiClientError(
                status_code=0,
                code="NETWORK_ERROR",
                message=f"Unable to communicate with ReproTrack backend at {url}: {exc}",
            )

    # ------------------ Auth API ------------------
    def login(self, identifier: str, password: str) -> dict:
        data = self._request(
            "POST", "/auth/login", json_data={"identifier": identifier, "password": password}
        )
        if "token" in data:
            self.set_token(data["token"])
        return data

    def logout(self) -> None:
        try:
            self._request("POST", "/auth/logout")
        finally:
            self.clear_token()

    def get_me(self) -> dict:
        return self._request("GET", "/auth/me")

    # ------------------ Dashboard API ------------------
    def get_dashboard_summary(self) -> dict:
        return self._request("GET", "/dashboard/summary")

    def get_recent_activity(self, limit: int = 15) -> List[dict]:
        return self._request("GET", "/dashboard/recent-activity", params={"limit": limit})

    # ------------------ Projects API ------------------
    def list_projects(self) -> List[dict]:
        return self._request("GET", "/projects")

    def create_project(self, key: str, name: str, description: str = "") -> dict:
        return self._request(
            "POST", "/projects", json_data={"key": key, "name": name, "description": description}
        )

    def get_project(self, project_id: int) -> dict:
        return self._request("GET", f"/projects/{project_id}")

    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> dict:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if is_active is not None:
            payload["is_active"] = is_active
        return self._request("PATCH", f"/projects/{project_id}", json_data=payload)

    def list_project_members(self, project_id: int) -> List[dict]:
        return self._request("GET", f"/projects/{project_id}/members")

    def add_project_member(self, project_id: int, user_id: int, role: str) -> dict:
        return self._request(
            "POST", f"/projects/{project_id}/members", json_data={"user_id": user_id, "role": role}
        )

    def remove_project_member(self, project_id: int, user_id: int) -> None:
        self._request("DELETE", f"/projects/{project_id}/members/{user_id}")

    # ------------------ Issues API ------------------
    def list_issues(
        self,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> dict:
        return self._request(
            "GET",
            "/issues",
            params={
                "project_id": project_id,
                "status": status,
                "severity": severity,
                "priority": priority,
                "assignee_id": assignee_id,
                "search": search,
                "page": page,
                "page_size": page_size,
                "sort_by": sort_by,
                "sort_dir": sort_dir,
            },
        )

    def create_issue(
        self,
        project_id: int,
        title: str,
        description: str,
        steps_to_reproduce: str,
        expected_result: str,
        actual_result: str,
        environment: Optional[str] = None,
        severity: str = "MEDIUM",
        priority: str = "NORMAL",
        assignee_id: Optional[int] = None,
        due_at: Optional[str] = None,
    ) -> dict:
        payload = {
            "project_id": project_id,
            "title": title,
            "description": description,
            "steps_to_reproduce": steps_to_reproduce,
            "expected_result": expected_result,
            "actual_result": actual_result,
            "environment": environment,
            "severity": severity,
            "priority": priority,
            "assignee_id": assignee_id,
            "due_at": due_at,
        }
        return self._request("POST", "/issues", json_data=payload)

    def get_issue(self, issue_id: int) -> dict:
        return self._request("GET", f"/issues/{issue_id}")

    def update_issue_metadata(
        self,
        issue_id: int,
        version: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        steps_to_reproduce: Optional[str] = None,
        expected_result: Optional[str] = None,
        actual_result: Optional[str] = None,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> dict:
        payload = {"version": version}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if steps_to_reproduce is not None:
            payload["steps_to_reproduce"] = steps_to_reproduce
        if expected_result is not None:
            payload["expected_result"] = expected_result
        if actual_result is not None:
            payload["actual_result"] = actual_result
        if environment is not None:
            payload["environment"] = environment
        if severity is not None:
            payload["severity"] = severity
        if priority is not None:
            payload["priority"] = priority
        return self._request("PATCH", f"/issues/{issue_id}", json_data=payload)

    def assign_issue(self, issue_id: int, assignee_id: Optional[int], version: int) -> dict:
        return self._request(
            "POST",
            f"/issues/{issue_id}/assign",
            json_data={"assignee_id": assignee_id, "version": version},
        )

    def transition_issue(
        self, issue_id: int, new_status: str, version: int, reason: Optional[str] = None
    ) -> dict:
        return self._request(
            "POST",
            f"/issues/{issue_id}/transition",
            json_data={"new_status": new_status, "version": version, "reason": reason},
        )

    def list_issue_comments(self, issue_id: int) -> List[dict]:
        return self._request("GET", f"/issues/{issue_id}/comments")

    def add_issue_comment(self, issue_id: int, body: str) -> dict:
        return self._request("POST", f"/issues/{issue_id}/comments", json_data={"body": body})

    def list_issue_events(self, issue_id: int) -> List[dict]:
        return self._request("GET", f"/issues/{issue_id}/events")

    def list_issue_verifications(self, issue_id: int) -> List[dict]:
        return self._request("GET", f"/issues/{issue_id}/verifications")

    # ------------------ Verification API ------------------
    def get_pending_verifications(self, project_id: Optional[int] = None) -> List[dict]:
        return self._request("GET", "/verification/pending", params={"project_id": project_id})

    def submit_verification(
        self, issue_id: int, result: str, test_notes: str, tested_version: str
    ) -> dict:
        return self._request(
            "POST",
            f"/issues/{issue_id}/verify",
            json_data={
                "result": result,
                "test_notes": test_notes,
                "tested_version": tested_version,
            },
        )

    # ------------------ Reports API ------------------
    def get_status_breakdown(self, project_id: Optional[int] = None) -> List[dict]:
        return self._request("GET", "/reports/status-breakdown", params={"project_id": project_id})

    def get_severity_breakdown(self, project_id: Optional[int] = None) -> List[dict]:
        return self._request(
            "GET", "/reports/severity-breakdown", params={"project_id": project_id}
        )

    def get_resolution_time(self, project_id: Optional[int] = None) -> dict:
        return self._request("GET", "/reports/resolution-time", params={"project_id": project_id})

    def get_reopened_rate(self, project_id: Optional[int] = None) -> dict:
        return self._request("GET", "/reports/reopened-rate", params={"project_id": project_id})

    def get_backlog_age(self, project_id: Optional[int] = None) -> dict:
        return self._request("GET", "/reports/backlog-age", params={"project_id": project_id})

    # ------------------ Users API (Admin) ------------------
    def list_users(self) -> List[dict]:
        return self._request("GET", "/users")

    def create_user(
        self, display_name: str, email: str, password: str, global_role: str = "USER"
    ) -> dict:
        return self._request(
            "POST",
            "/users",
            json_data={
                "display_name": display_name,
                "email": email,
                "password": password,
                "global_role": global_role,
            },
        )

    def update_user(
        self, user_id: int, display_name: Optional[str] = None, global_role: Optional[str] = None
    ) -> dict:
        payload = {}
        if display_name:
            payload["display_name"] = display_name
        if global_role:
            payload["global_role"] = global_role
        return self._request("PATCH", f"/users/{user_id}", json_data=payload)

    def deactivate_user(self, user_id: int) -> dict:
        return self._request("POST", f"/users/{user_id}/deactivate")

    def list_audit_events(self, limit: int = 50) -> List[dict]:
        return self._request("GET", "/users/audit-log", params={"limit": limit})

    # ------------------ System API ------------------
    def get_system_health(self) -> dict:
        return self._request("GET", "/system/health")

    def get_system_diagnostics(self) -> dict:
        return self._request("GET", "/system/diagnostics")
