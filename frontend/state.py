"""Shared session and UI state for ReproTrack frontend."""

from typing import Any, Callable, Dict, Optional


class AppState:
    def __init__(self):
        self.current_user: Optional[Dict[str, Any]] = None
        self.token: Optional[str] = None
        self.active_project_id: Optional[int] = None
        self.active_project_key: Optional[str] = None
        self.active_project_name: Optional[str] = None
        self.navigate: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None
        self.show_message: Optional[Callable[[str, bool], None]] = None

    @property
    def is_authenticated(self) -> bool:
        return self.current_user is not None and self.token is not None

    @property
    def is_global_admin(self) -> bool:
        if not self.current_user:
            return False
        return self.current_user.get("global_role") == "GLOBAL_ADMIN"

    def clear(self) -> None:
        self.current_user = None
        self.token = None
        self.active_project_id = None
        self.active_project_key = None
        self.active_project_name = None


state = AppState()
