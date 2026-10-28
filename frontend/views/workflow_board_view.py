"""Workflow Board view (Kanban columns grouped by bug lifecycle stages)."""

from typing import Dict, List

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.badges import build_severity_badge
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography

COLUMNS = [
    ("REPORTED", "1. Reported", Colors.BADGE_TRIAGE_TEXT),
    ("TRIAGED", "2. Triaged", Colors.INFO),
    ("IN_PROGRESS", "3. In Progress", Colors.BADGE_IN_PROGRESS_TEXT),
    ("FIXED", "4. Fixed", Colors.WARNING),
    ("IN_VERIFICATION", "5. In Verification", Colors.ACTION_MINT),
    ("CLOSED", "6. Closed / Verified", Colors.SUCCESS),
]


def build_workflow_board_view(api_client: ReproTrackApiClient, page: ft.Page) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    project_dropdown = ft.Dropdown(label="Project", width=200, height=40, text_size=12)
    board_container = ft.Container(expand=True)

    def load_projects_filter():
        try:
            projs = api_client.list_projects()
            options = [ft.dropdown.Option("", "All Accessible Projects")]
            for p in projs:
                options.append(ft.dropdown.Option(str(p["id"]), f"{p['key']} - {p['name']}"))
            project_dropdown.options = options
            if state.active_project_id:
                project_dropdown.value = str(state.active_project_id)
            else:
                project_dropdown.value = ""
        except Exception:
            pass

    def load_board():
        board_container.content = build_loading_state("Loading workflow board...")
        board_container.update()

        p_id = int(project_dropdown.value) if project_dropdown.value else None

        try:
            res = api_client.list_issues(project_id=p_id, page=1, page_size=100)
            issues = res.get("items", [])
        except ApiClientError as err:
            board_container.content = build_error_banner(
                err.message, on_retry=lambda _: load_board()
            )
            board_container.update()
            return

        # Group issues by status
        buckets: Dict[str, List[dict]] = {col[0]: [] for col in COLUMNS}
        # Also group REOPENED into IN_PROGRESS or REPORTED
        for iss in issues:
            st = iss.get("status", "REPORTED")
            if st in buckets:
                buckets[st].append(iss)
            elif st == "REOPENED":
                # Show reopened prominently in TRIAGED/IN_PROGRESS bucket
                if "TRIAGED" in buckets:
                    buckets["TRIAGED"].append(iss)
            elif st == "WONT_FIX":
                if "CLOSED" in buckets:
                    buckets["CLOSED"].append(iss)

        column_controls = []
        for col_status, col_title, accent_color in COLUMNS:
            col_issues = buckets.get(col_status, [])

            cards = []
            for item in col_issues:
                iss_id = item["id"]
                iss_key = item["issue_key"]
                title = item["title"]
                sev = item["severity"]
                assignee = item.get("assignee_name") or "Unassigned"

                def make_open_handler(target_id: int):
                    return lambda _: (
                        state.navigate("issue_details", {"issue_id": target_id})
                        if state.navigate
                        else None
                    )

                card = ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        iss_key,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        font_family=Typography.FONT_MONO,
                                        color=Colors.INFO,
                                    ),
                                    build_severity_badge(sev),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                title,
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=Colors.MAIN_TEXT,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.PERSON_OUTLINE,
                                                size=13,
                                                color=Colors.SECONDARY_TEXT,
                                            ),
                                            ft.Text(assignee, size=11, color=Colors.SECONDARY_TEXT),
                                        ],
                                        spacing=4,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.OPEN_IN_NEW,
                                        icon_size=14,
                                        tooltip="Inspect Details",
                                        on_click=make_open_handler(iss_id),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=Colors.SURFACE_CARD,
                    border=ft.border.all(1, Colors.BORDER),
                    border_radius=Radii.STANDARD,
                    padding=ft.padding.all(12),
                    ink=True,
                    on_click=make_open_handler(iss_id),
                )
                cards.append(card)

            col_container = ft.Container(
                content=ft.Column(
                    controls=[
                        # Column Header
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        col_title,
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=Colors.MAIN_TEXT,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            str(len(col_issues)),
                                            size=10,
                                            weight=ft.FontWeight.BOLD,
                                            color=Colors.SURFACE_CARD,
                                        ),
                                        bgcolor=accent_color,
                                        border_radius=Radii.STANDARD,
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            bgcolor=Colors.SURFACE_LOW,
                            border_radius=Radii.STANDARD,
                            padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        ),
                        # Cards Column
                        ft.Column(
                            controls=cards
                            if cards
                            else [ft.Text("No defects", size=11, color=Colors.MUTED_TEXT)],
                            spacing=8,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    expand=True,
                ),
                width=240,
                bgcolor=Colors.CANVAS_BASE,
                border=ft.border.all(1, Colors.BORDER),
                border_radius=Radii.CARD,
                padding=ft.padding.all(8),
            )
            column_controls.append(col_container)

        board_row = ft.Row(
            controls=column_controls,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.START,
            height=600,
        )

        board_container.content = board_row
        board_container.update()

    project_dropdown.on_change = lambda _: load_board()

    header_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Workflow Board",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY_NAVY,
                        ),
                        ft.Text(
                            "Enforced state transitions across the bug resolution lifecycle.",
                            size=12,
                            color=Colors.SECONDARY_TEXT,
                        ),
                    ],
                    spacing=2,
                ),
                ft.Row(
                    controls=[
                        project_dropdown,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Refresh",
                            on_click=lambda _: load_board(),
                        ),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.CARD,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )

    main_column.controls.extend(
        [
            header_bar,
            board_container,
        ]
    )

    load_projects_filter()
    load_board()
    return main_column
