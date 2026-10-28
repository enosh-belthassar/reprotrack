"""Analytical Reports view with defect distributions, resolution times, and reopen rates."""

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.badges import build_severity_badge, build_status_badge
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_reports_view(api_client: ReproTrackApiClient, page: ft.Page) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    project_dropdown = ft.Dropdown(label="Project Filter", width=220, height=40, text_size=12)
    reports_container = ft.Container(expand=True)

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

    def load_reports():
        reports_container.content = build_loading_state("Computing real platform metrics...")
        reports_container.update()

        p_id = int(project_dropdown.value) if project_dropdown.value else None

        try:
            status_data = api_client.get_status_breakdown(project_id=p_id)
            sev_data = api_client.get_severity_breakdown(project_id=p_id)
            res_time = api_client.get_resolution_time(project_id=p_id)
            reopened = api_client.get_reopened_rate(project_id=p_id)
            backlog = api_client.get_backlog_age(project_id=p_id)
        except ApiClientError as err:
            reports_container.content = build_error_banner(
                err.message, on_retry=lambda _: load_reports()
            )
            reports_container.update()
            return

        # 1. KPI Summary Cards
        avg_h = res_time.get("average_hours", 0.0)
        med_h = res_time.get("median_hours", 0.0)
        res_count = res_time.get("resolved_count", 0)

        reopen_rate = reopened.get("reopened_rate_percentage", 0.0)
        total_verif = reopened.get("total_verified_count", 0)
        reopened_count = reopened.get("reopened_count", 0)

        total_open = backlog.get("total_open", 0)
        under_7 = backlog.get("under_7_days", 0)
        between_7_30 = backlog.get("from_7_to_30_days", 0)
        over_30 = backlog.get("over_30_days", 0)

        metric_cards = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "MEAN RESOLUTION TIME",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.SECONDARY_TEXT,
                        ),
                        ft.Text(
                            f"{avg_h:.1f} hrs",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY_NAVY,
                            font_family=Typography.FONT_MONO,
                        ),
                        ft.Text(
                            f"Median: {med_h:.1f}h ({res_count} resolved)",
                            size=11,
                            color=Colors.MUTED_TEXT,
                        ),
                    ],
                    spacing=4,
                ),
                width=240,
                bgcolor=Colors.SURFACE_CARD,
                border=ft.border.all(1, Colors.BORDER),
                border_radius=Radii.CARD,
                padding=ft.padding.all(16),
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "DEFECT REOPEN RATE",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.SECONDARY_TEXT,
                        ),
                        ft.Text(
                            f"{reopen_rate:.1f}%",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.ERROR if reopen_rate > 20 else Colors.PRIMARY_NAVY,
                            font_family=Typography.FONT_MONO,
                        ),
                        ft.Text(
                            f"{reopened_count} of {total_verif} runs failed verification",
                            size=11,
                            color=Colors.MUTED_TEXT,
                        ),
                    ],
                    spacing=4,
                ),
                width=240,
                bgcolor=Colors.SURFACE_CARD,
                border=ft.border.all(1, Colors.BORDER),
                border_radius=Radii.CARD,
                padding=ft.padding.all(16),
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "BACKLOG AGE HEALTH",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.SECONDARY_TEXT,
                        ),
                        ft.Text(
                            f"{total_open} Open",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY_NAVY,
                            font_family=Typography.FONT_MONO,
                        ),
                        ft.Text(
                            f"<7d: {under_7} | 7-30d: {between_7_30} | >30d: {over_30}",
                            size=11,
                            color=Colors.MUTED_TEXT,
                        ),
                    ],
                    spacing=4,
                ),
                width=260,
                bgcolor=Colors.SURFACE_CARD,
                border=ft.border.all(1, Colors.BORDER),
                border_radius=Radii.CARD,
                padding=ft.padding.all(16),
            ),
        ]

        top_kpi_row = ft.Row(controls=metric_cards, spacing=16, wrap=True)

        # 2. Status Breakdown Table & Visual Bars
        status_rows = []
        for s in status_data:
            st_name = s["status"]
            cnt = s["count"]
            status_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(build_status_badge(st_name)),
                        ft.DataCell(
                            ft.Text(
                                str(cnt),
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                    ]
                )
            )

        status_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("LIFECYCLE STATUS", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("COUNT", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=status_rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=24,
        )

        status_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Defect Counts by Status",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    status_table
                    if status_rows
                    else ft.Text("No data available.", size=11, color=Colors.MUTED_TEXT),
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
            width=360,
        )

        # 3. Severity Breakdown Table
        sev_rows = []
        for sv in sev_data:
            s_name = sv["severity"]
            cnt = sv["count"]
            sev_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(build_severity_badge(s_name)),
                        ft.DataCell(
                            ft.Text(
                                str(cnt),
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                    ]
                )
            )

        sev_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("SEVERITY", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("COUNT", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=sev_rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=24,
        )

        sev_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Defect Counts by Severity",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    sev_table
                    if sev_rows
                    else ft.Text("No data available.", size=11, color=Colors.MUTED_TEXT),
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
            width=360,
        )

        tables_row = ft.Row(
            controls=[status_card, sev_card],
            spacing=16,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        reports_container.content = ft.Column(
            controls=[
                top_kpi_row,
                ft.Divider(height=16, color="transparent"),
                tables_row,
            ],
            spacing=12,
        )
        reports_container.update()

    project_dropdown.on_change = lambda _: load_reports()

    header_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Quality & Velocity Reports",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY_NAVY,
                        ),
                        ft.Text(
                            "Database-grounded defect metrics, resolution velocity, and verification stability.",
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
                            tooltip="Recalculate",
                            on_click=lambda _: load_reports(),
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
            reports_container,
        ]
    )

    load_projects_filter()
    load_reports()
    return main_column
