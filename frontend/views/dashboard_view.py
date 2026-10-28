"""Dashboard view with KPI metric cards, recent activity, and quick navigation."""

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_dashboard_view(api_client: ReproTrackApiClient) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=20)

    loading_box = build_loading_state("Loading dashboard metrics...")
    main_column.controls.append(loading_box)

    def load_data():
        main_column.controls.clear()
        try:
            summary = api_client.get_dashboard_summary()
            recent_activity = api_client.get_recent_activity(limit=10)
        except ApiClientError as err:
            main_column.controls.append(
                build_error_banner(err.message, on_retry=lambda _: load_data())
            )
            main_column.update()
            return

        # 1. KPI Cards
        kpi_configs = [
            (
                "Accessible Projects",
                summary.get("accessible_projects_count", 0),
                Colors.PRIMARY_NAVY,
                ft.Icons.FOLDER_OUTLINED,
            ),
            (
                "Open Defects",
                summary.get("open_issues_count", 0),
                Colors.INFO,
                ft.Icons.BUG_REPORT_OUTLINED,
            ),
            (
                "Critical / High",
                summary.get("critical_high_count", 0),
                Colors.ERROR,
                ft.Icons.WARNING_AMBER_OUTLINED,
            ),
            (
                "In Progress",
                summary.get("in_progress_count", 0),
                Colors.BADGE_IN_PROGRESS_TEXT,
                ft.Icons.PENDING_ACTIONS_OUTLINED,
            ),
            (
                "Awaiting Verification",
                summary.get("fixed_awaiting_verification_count", 0),
                Colors.ACTION_MINT,
                ft.Icons.VERIFIED_OUTLINED,
            ),
            (
                "Reopened",
                summary.get("reopened_count", 0),
                Colors.WARNING,
                ft.Icons.REPLAY_OUTLINED,
            ),
            (
                "Overdue",
                summary.get("overdue_count", 0),
                Colors.ERROR,
                ft.Icons.EVENT_BUSY_OUTLINED,
            ),
        ]

        cards = []
        for title, val, color, icon in kpi_configs:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        title,
                                        size=11,
                                        color=Colors.SECONDARY_TEXT,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    ft.Icon(icon, size=16, color=color),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                str(val),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.MAIN_TEXT,
                                font_family=Typography.FONT_MONO,
                            ),
                        ],
                        spacing=6,
                    ),
                    width=180,
                    bgcolor=Colors.SURFACE_CARD,
                    border=ft.border.all(1, Colors.BORDER),
                    border_radius=Radii.CARD,
                    padding=ft.padding.all(16),
                )
            )

        kpi_row = ft.Row(controls=cards, wrap=True, spacing=16)

        # 2. Quick Actions
        quick_actions = ft.Row(
            controls=[
                ft.ElevatedButton(
                    text="Report New Issue",
                    icon=ft.Icons.ADD,
                    bgcolor=Colors.ACTION_MINT,
                    color=Colors.SURFACE_CARD,
                    height=36,
                    on_click=lambda _: (
                        state.navigate("issues", {"open_create": True}) if state.navigate else None
                    ),
                ),
                ft.OutlinedButton(
                    text="Workflow Board",
                    icon=ft.Icons.VIEW_KANBAN_OUTLINED,
                    height=36,
                    on_click=lambda _: state.navigate("board") if state.navigate else None,
                ),
                ft.OutlinedButton(
                    text="Fix Verification Console",
                    icon=ft.Icons.VERIFIED_OUTLINED,
                    height=36,
                    on_click=lambda _: state.navigate("verification") if state.navigate else None,
                ),
            ],
            spacing=12,
        )

        # 3. Recent Activity Section
        activity_rows = []
        if recent_activity:
            for act in recent_activity:
                time_str = act.get("timestamp", "")
                if "T" in time_str:
                    time_str = time_str.split("T")[0] + " " + time_str.split("T")[1][:5]

                activity_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Text(
                                    act.get("issue_key", ""),
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    font_family=Typography.FONT_MONO,
                                    color=Colors.INFO,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    act.get("issue_title", "")[:40], size=12, color=Colors.MAIN_TEXT
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    act.get("actor_name", "System"),
                                    size=12,
                                    color=Colors.SECONDARY_TEXT,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    act.get("event_type", ""),
                                    size=11,
                                    color=Colors.PRIMARY_NAVY,
                                    weight=ft.FontWeight.W_600,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    f"{act.get('old_value') or ''} -> {act.get('new_value') or ''}",
                                    size=11,
                                    color=Colors.SECONDARY_TEXT,
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    time_str,
                                    size=11,
                                    color=Colors.MUTED_TEXT,
                                    font_family=Typography.FONT_MONO,
                                )
                            ),
                        ]
                    )
                )

        activity_table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text("KEY", size=11, weight=ft.FontWeight.BOLD, color=Colors.SECONDARY_TEXT)
                ),
                ft.DataColumn(
                    ft.Text(
                        "TITLE", size=11, weight=ft.FontWeight.BOLD, color=Colors.SECONDARY_TEXT
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "ACTOR", size=11, weight=ft.FontWeight.BOLD, color=Colors.SECONDARY_TEXT
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "EVENT", size=11, weight=ft.FontWeight.BOLD, color=Colors.SECONDARY_TEXT
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "CHANGE", size=11, weight=ft.FontWeight.BOLD, color=Colors.SECONDARY_TEXT
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "TIME (UTC)",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    )
                ),
            ],
            rows=activity_rows,
            heading_row_color=Colors.SURFACE_LOW,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.STANDARD,
            horizontal_margin=16,
            column_spacing=20,
        )

        activity_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Recent Lifecycle & Audit Activity",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.MAIN_TEXT,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                icon_size=18,
                                tooltip="Refresh",
                                on_click=lambda _: load_data(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(content=activity_table, border_radius=Radii.STANDARD),
                ],
                spacing=12,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(20),
        )

        main_column.controls.extend(
            [
                ft.Text(
                    "Platform Overview",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=Colors.PRIMARY_NAVY,
                ),
                kpi_row,
                ft.Divider(height=16, color="transparent"),
                quick_actions,
                ft.Divider(height=24, color="transparent"),
                activity_card,
            ]
        )
        main_column.update()

    # Initial load
    load_data()
    return main_column
