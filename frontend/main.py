"""ReproTrack Flet desktop and web frontend application entrypoint."""

from typing import Any, Dict, Optional

import flet as ft

import frontend.flet_compat  # noqa: F401
from frontend.api_client import ReproTrackApiClient
from frontend.components.layout import build_app_shell
from frontend.state import state
from frontend.tokens import Colors
from frontend.views.dashboard_view import build_dashboard_view
from frontend.views.fix_verification_view import build_fix_verification_view
from frontend.views.issue_details_view import build_issue_details_view
from frontend.views.issues_view import build_issues_view

# Views
from frontend.views.login_view import build_login_view
from frontend.views.projects_view import build_projects_view
from frontend.views.reports_view import build_reports_view
from frontend.views.settings_view import build_settings_view
from frontend.views.user_mgmt_view import build_user_mgmt_view
from frontend.views.workflow_board_view import build_workflow_board_view


def main(page: ft.Page):
    page.title = "ReproTrack — Bug Reporting, Testing & Fix Verification Platform"
    page.bgcolor = Colors.CANVAS_BASE
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    # Toast / SnackBar helper
    snack_bar = ft.SnackBar(content=ft.Text(""), open=False)
    page.overlay.append(snack_bar)

    def show_toast(message: str, is_error: bool = False):
        snack_bar.content = ft.Text(message, color=Colors.SURFACE_CARD)
        snack_bar.bgcolor = Colors.ERROR if is_error else Colors.PRIMARY_NAVY
        snack_bar.open = True
        page.update()

    state.show_message = show_toast

    # Instantiate API client with auto-logout on unauthorized
    def handle_unauthorized():
        state.clear()
        navigate("login")
        show_toast("Session expired or unauthorized. Please sign in again.", True)

    api_client = ReproTrackApiClient(on_unauthorized=handle_unauthorized)

    # Current view tracking
    current_view_key = "login"
    current_params: Optional[Dict[str, Any]] = None

    def navigate(view_key: str, params: Optional[Dict[str, Any]] = None):
        nonlocal current_view_key, current_params
        current_view_key = view_key
        current_params = params

        page.controls.clear()

        # Login Guard
        if not state.is_authenticated and view_key != "login":
            view_key = "login"
            current_view_key = "login"

        if view_key == "login":
            page.controls.append(
                build_login_view(api_client, on_login_success=lambda: navigate("dashboard"))
            )
        else:
            # Render inner view
            view_control = None
            if view_key == "dashboard":
                view_control = build_dashboard_view(api_client)
            elif view_key == "projects":
                view_control = build_projects_view(api_client, page)
            elif view_key == "issues":
                view_control = build_issues_view(api_client, page, current_params)
            elif view_key == "issue_details":
                view_control = build_issue_details_view(api_client, page, current_params)
            elif view_key == "board":
                view_control = build_workflow_board_view(api_client, page)
            elif view_key == "verification":
                view_control = build_fix_verification_view(api_client, page, current_params)
            elif view_key == "reports":
                view_control = build_reports_view(api_client, page)
            elif view_key == "users":
                view_control = build_user_mgmt_view(api_client, page)
            elif view_key == "settings":
                view_control = build_settings_view(api_client, page)
            else:
                view_control = build_dashboard_view(api_client)

            # Wrap in app shell
            shell = build_app_shell(
                page=page,
                current_view_key=current_view_key,
                content_control=view_control,
                on_logout=lambda: handle_logout(),
            )
            page.controls.append(shell)

        page.update()

    def handle_logout():
        try:
            api_client.logout()
        except Exception:
            pass
        state.clear()
        navigate("login")
        show_toast("Successfully signed out.", False)

    state.navigate = navigate

    # Initial view
    navigate("login")


if __name__ == "__main__":
    import os

    view_mode = os.getenv("FLET_VIEW", "flet_app").lower()
    app_view = ft.AppView.WEB_BROWSER if view_mode == "web" else ft.AppView.FLET_APP
    port = int(os.getenv("FLET_PORT", "8550")) if view_mode == "web" else 0

    if hasattr(ft, "run"):
        ft.run(main, view=app_view, port=port)
    elif hasattr(ft, "app"):
        getattr(ft, "app")(target=main, view=app_view, port=port)
