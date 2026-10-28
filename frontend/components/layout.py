"""App shell layout, navigation rail, and header chrome."""

from typing import Callable

import flet as ft

from frontend.state import state
from frontend.tokens import Colors, Radii, Typography

NAV_ITEMS = [
    ("dashboard", "Dashboard", ft.Icons.DASHBOARD_OUTLINED),
    ("projects", "Projects", ft.Icons.FOLDER_OUTLINED),
    ("issues", "Issues", ft.Icons.BUG_REPORT_OUTLINED),
    ("board", "Workflow Board", ft.Icons.VIEW_KANBAN_OUTLINED),
    ("verification", "Fix Verification", ft.Icons.VERIFIED_OUTLINED),
    ("reports", "Reports", ft.Icons.INSIGHTS_OUTLINED),
    ("users", "User Management", ft.Icons.PEOPLE_OUTLINE),
    ("settings", "Settings", ft.Icons.SETTINGS_OUTLINED),
]


def build_app_shell(
    page: ft.Page,
    current_view_key: str,
    content_control: ft.Control,
    on_logout: Callable[[], None],
) -> ft.Row:
    # 1. Sidebar Nav
    sidebar_items = []

    # App Brand Header
    brand_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.BUG_REPORT, size=24, color=Colors.ACTION_MINT),
                ft.Column(
                    controls=[
                        ft.Text(
                            "REPROTRACK",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.ON_NAVY_TEXT,
                            font_family=Typography.FONT_MONO,
                        ),
                        ft.Text(
                            "TEST & FIX VERIFY",
                            size=9,
                            color=Colors.ON_NAVY_MUTED,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=1,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=16, right=16, top=20, bottom=24),
    )
    sidebar_items.append(brand_row)

    # Nav links
    for key, label, icon in NAV_ITEMS:
        # Hide admin-only users link for non-admins
        if key == "users" and not state.is_global_admin:
            continue

        is_active = key == current_view_key

        def make_click_handler(route_key: str):
            return lambda _: state.navigate(route_key) if state.navigate else None

        bg = Colors.SECONDARY_NAVY if is_active else None
        fg = Colors.ON_NAVY_TEXT if is_active else Colors.ON_NAVY_MUTED

        item_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=3,
                        height=20,
                        bgcolor=Colors.ACTION_MINT if is_active else "transparent",
                        border_radius=2,
                    ),
                    ft.Icon(icon, size=18, color=Colors.ACTION_MINT if is_active else fg),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL,
                        color=fg,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=bg,
            border_radius=Radii.STANDARD,
            padding=ft.padding.symmetric(horizontal=8, vertical=10),
            ink=True,
            on_click=make_click_handler(key),
        )
        sidebar_items.append(item_btn)

    sidebar_col = ft.Column(
        controls=sidebar_items,
        spacing=4,
        expand=True,
    )

    sidebar_container = ft.Container(
        content=sidebar_col,
        width=230,
        bgcolor=Colors.PRIMARY_NAVY,
        padding=ft.padding.symmetric(horizontal=8),
    )

    # 2. Top Header Bar
    user_name = state.current_user.get("display_name", "User") if state.current_user else "User"
    user_role = state.current_user.get("global_role", "USER") if state.current_user else "USER"

    top_bar = ft.Container(
        content=ft.Row(
            controls=[
                # Breadcrumb / Page Title
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.NAVIGATE_NEXT, size=16, color=Colors.SECONDARY_TEXT),
                        ft.Text(
                            current_view_key.replace("_", " ").upper(),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.MAIN_TEXT,
                            font_family=Typography.FONT_MONO,
                        ),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Right Profile & Actions
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.CircleAvatar(
                                        content=ft.Text(
                                            user_name[:2].upper(),
                                            size=11,
                                            color=Colors.ON_NAVY_TEXT,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        radius=14,
                                        bgcolor=Colors.SECONDARY_NAVY,
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                user_name,
                                                size=12,
                                                weight=ft.FontWeight.W_600,
                                                color=Colors.MAIN_TEXT,
                                            ),
                                            ft.Text(
                                                user_role,
                                                size=10,
                                                color=Colors.SECONDARY_TEXT,
                                                font_family=Typography.FONT_MONO,
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT_OUTLINED,
                            icon_size=18,
                            icon_color=Colors.SECONDARY_TEXT,
                            tooltip="Sign Out",
                            on_click=lambda _: on_logout(),
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        height=54,
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
        padding=ft.padding.symmetric(horizontal=24),
    )

    # 3. Main Workspace Canvas
    workspace_canvas = ft.Container(
        content=ft.Column(
            controls=[
                top_bar,
                ft.Container(
                    content=content_control,
                    expand=True,
                    padding=ft.padding.all(24),
                ),
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
        bgcolor=Colors.CANVAS_BASE,
    )

    return ft.Row(
        controls=[
            sidebar_container,
            workspace_canvas,
        ],
        expand=True,
        spacing=0,
    )
