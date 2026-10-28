"""Issues list view with multi-dimensional filtering, pagination, and defect reporting modal."""

from typing import Any, Dict, Optional

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.badges import build_severity_badge, build_status_badge
from frontend.components.feedback import build_empty_state, build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_issues_view(
    api_client: ReproTrackApiClient,
    page: ft.Page,
    params: Optional[Dict[str, Any]] = None,
) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    # Current filter & pagination state
    current_page = 1
    page_size = 15
    total_count = 0

    # Filter controls
    project_dropdown = ft.Dropdown(label="Project", width=160, height=40, text_size=12)
    status_dropdown = ft.Dropdown(
        label="Status",
        width=140,
        height=40,
        text_size=12,
        options=[
            ft.dropdown.Option("", "All Statuses"),
            ft.dropdown.Option("REPORTED"),
            ft.dropdown.Option("TRIAGED"),
            ft.dropdown.Option("IN_PROGRESS"),
            ft.dropdown.Option("FIXED"),
            ft.dropdown.Option("IN_VERIFICATION"),
            ft.dropdown.Option("CLOSED"),
            ft.dropdown.Option("REOPENED"),
            ft.dropdown.Option("WONT_FIX"),
        ],
        value="",
    )
    severity_dropdown = ft.Dropdown(
        label="Severity",
        width=130,
        height=40,
        text_size=12,
        options=[
            ft.dropdown.Option("", "All Severities"),
            ft.dropdown.Option("CRITICAL"),
            ft.dropdown.Option("HIGH"),
            ft.dropdown.Option("MEDIUM"),
            ft.dropdown.Option("LOW"),
        ],
        value="",
    )
    search_input = ft.TextField(
        label="Search title / key / desc",
        width=200,
        height=40,
        text_size=12,
        prefix_icon=ft.Icons.SEARCH,
    )

    table_container = ft.Container(expand=True)
    pagination_text = ft.Text("Page 1 of 1", size=12, color=Colors.SECONDARY_TEXT)
    prev_btn = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_size=18)
    next_btn = ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_size=18)

    create_modal = ft.AlertDialog(modal=True)

    def load_projects_filter():
        try:
            projs = api_client.list_projects()
            options = [ft.dropdown.Option("", "All Projects")]
            for p in projs:
                options.append(ft.dropdown.Option(str(p["id"]), f"{p['key']} - {p['name']}"))
            project_dropdown.options = options
            if state.active_project_id:
                project_dropdown.value = str(state.active_project_id)
            else:
                project_dropdown.value = ""
        except Exception:
            pass

    def fetch_issues():
        nonlocal current_page, total_count
        table_container.content = build_loading_state("Loading issues from server...")
        table_container.update()

        p_id = int(project_dropdown.value) if project_dropdown.value else None
        st = status_dropdown.value if status_dropdown.value else None
        sv = severity_dropdown.value if severity_dropdown.value else None
        srch = search_input.value.strip() if search_input.value else None

        try:
            res = api_client.list_issues(
                project_id=p_id,
                status=st,
                severity=sv,
                search=srch,
                page=current_page,
                page_size=page_size,
            )
            items = res.get("items", [])
            total_count = res.get("total", 0)
        except ApiClientError as err:
            table_container.content = build_error_banner(
                err.message, on_retry=lambda _: fetch_issues()
            )
            table_container.update()
            return

        if not items:
            table_container.content = build_empty_state(
                icon=ft.Icons.BUG_REPORT_OUTLINED,
                title="No issues found",
                subtitle="Try adjusting your filters or report a new defect.",
                action_text="Report Defect",
                on_action=lambda _: open_create_defect_modal(),
            )
            table_container.update()
            update_pagination_ui()
            return

        rows = []
        for item in items:
            iss_id = item["id"]
            iss_key = item["issue_key"]
            title = item["title"]
            proj_key = item.get("project_key", "")
            stat = item["status"]
            sev = item["severity"]
            assignee = item.get("assignee_name") or "Unassigned"
            created_str = item.get("created_at", "")[:10]

            def make_open_detail_handler(target_id: int):
                return lambda _: (
                    state.navigate("issue_details", {"issue_id": target_id})
                    if state.navigate
                    else None
                )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    iss_key,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    font_family=Typography.FONT_MONO,
                                    color=Colors.INFO,
                                ),
                                on_click=make_open_detail_handler(iss_id),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    title,
                                    size=12,
                                    color=Colors.MAIN_TEXT,
                                    weight=ft.FontWeight.W_500,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                on_click=make_open_detail_handler(iss_id),
                                width=260,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                proj_key,
                                size=11,
                                font_family=Typography.FONT_MONO,
                                color=Colors.SECONDARY_TEXT,
                            )
                        ),
                        ft.DataCell(build_status_badge(stat)),
                        ft.DataCell(build_severity_badge(sev)),
                        ft.DataCell(ft.Text(assignee, size=11, color=Colors.SECONDARY_TEXT)),
                        ft.DataCell(
                            ft.Text(
                                created_str,
                                size=11,
                                color=Colors.MUTED_TEXT,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.ARROW_FORWARD,
                                icon_size=16,
                                tooltip="View Details",
                                on_click=make_open_detail_handler(iss_id),
                            )
                        ),
                    ]
                )
            )

        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("KEY", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("SUMMARY", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PROJ", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("STATUS", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("SEVERITY", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ASSIGNEE", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("CREATED", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ACTION", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=14,
            horizontal_margin=12,
        )

        table_container.content = ft.Container(
            content=data_table,
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(8),
        )
        table_container.update()
        update_pagination_ui()

    def update_pagination_ui():
        max_page = max(1, (total_count + page_size - 1) // page_size)
        pagination_text.value = f"Page {current_page} of {max_page} ({total_count} total defects)"
        prev_btn.disabled = current_page <= 1
        next_btn.disabled = current_page >= max_page
        pagination_text.update()
        prev_btn.update()
        next_btn.update()

    def on_prev(_):
        nonlocal current_page
        if current_page > 1:
            current_page -= 1
            fetch_issues()

    def on_next(_):
        nonlocal current_page
        max_page = max(1, (total_count + page_size - 1) // page_size)
        if current_page < max_page:
            current_page += 1
            fetch_issues()

    prev_btn.on_click = on_prev
    next_btn.on_click = on_next

    # Wire filter change events
    project_dropdown.on_change = lambda _: on_filter_change()
    status_dropdown.on_change = lambda _: on_filter_change()
    severity_dropdown.on_change = lambda _: on_filter_change()
    search_input.on_submit = lambda _: on_filter_change()

    def on_filter_change():
        nonlocal current_page
        current_page = 1
        fetch_issues()

    # ------------------ Create Defect Modal ------------------
    def open_create_defect_modal():
        # Get accessible projects
        projs = []
        try:
            projs = api_client.list_projects()
        except Exception:
            pass

        if not projs:
            if state.show_message:
                state.show_message("Please create or join a project before reporting issues.", True)
            return

        proj_select = ft.Dropdown(
            label="Project *",
            options=[ft.dropdown.Option(str(p["id"]), f"{p['key']} - {p['name']}") for p in projs],
            value=str(state.active_project_id or projs[0]["id"]),
            height=44,
            text_size=12,
        )

        title_field = ft.TextField(
            label="Defect Summary / Title *", max_length=255, height=44, text_size=13
        )
        desc_field = ft.TextField(
            label="Description", multiline=True, min_lines=2, max_lines=4, text_size=12
        )
        steps_field = ft.TextField(
            label="Steps to Reproduce *",
            multiline=True,
            min_lines=2,
            max_lines=4,
            text_size=12,
            hint_text="1. Navigate to...\n2. Click on...\n3. Observe...",
        )
        expected_field = ft.TextField(
            label="Expected Result *", multiline=True, min_lines=1, max_lines=3, text_size=12
        )
        actual_field = ft.TextField(
            label="Actual Result *", multiline=True, min_lines=1, max_lines=3, text_size=12
        )
        env_field = ft.TextField(
            label="Environment / Build",
            height=44,
            text_size=12,
            hint_text="e.g. Chrome 122, Staging v1.4",
        )

        sev_select = ft.Dropdown(
            label="Severity",
            options=[
                ft.dropdown.Option("CRITICAL"),
                ft.dropdown.Option("HIGH"),
                ft.dropdown.Option("MEDIUM"),
                ft.dropdown.Option("LOW"),
            ],
            value="MEDIUM",
            height=44,
            text_size=12,
            width=150,
        )

        prio_select = ft.Dropdown(
            label="Priority",
            options=[
                ft.dropdown.Option("URGENT"),
                ft.dropdown.Option("HIGH"),
                ft.dropdown.Option("NORMAL"),
                ft.dropdown.Option("LOW"),
            ],
            value="NORMAL",
            height=44,
            text_size=12,
            width=150,
        )

        err_text = ft.Text(value="", color=Colors.ERROR, size=12, visible=False)
        submit_btn = ft.ElevatedButton(
            "Submit Defect Report", bgcolor=Colors.PRIMARY_NAVY, color=Colors.ON_NAVY_TEXT
        )

        def handle_submit(_):
            if (
                not title_field.value
                or not steps_field.value
                or not expected_field.value
                or not actual_field.value
            ):
                err_text.value = (
                    "Title, Steps to Reproduce, Expected, and Actual results are required."
                )
                err_text.visible = True
                err_text.update()
                return

            submit_btn.disabled = True
            submit_btn.update()

            try:
                new_iss = api_client.create_issue(
                    project_id=int(proj_select.value),
                    title=title_field.value.strip(),
                    description=desc_field.value.strip() if desc_field.value else "",
                    steps_to_reproduce=steps_field.value.strip(),
                    expected_result=expected_field.value.strip(),
                    actual_result=actual_field.value.strip(),
                    environment=env_field.value.strip() if env_field.value else None,
                    severity=sev_select.value,
                    priority=prio_select.value,
                )
                create_modal.open = False
                page.update()
                if state.show_message:
                    state.show_message(
                        f"Defect {new_iss['issue_key']} created successfully.", False
                    )
                fetch_issues()
            except ApiClientError as err:
                err_text.value = err.message
                err_text.visible = True
                submit_btn.disabled = False
                err_text.update()
                submit_btn.update()

        submit_btn.on_click = handle_submit

        modal_body = ft.Container(
            content=ft.Column(
                controls=[
                    proj_select,
                    title_field,
                    desc_field,
                    steps_field,
                    ft.Row(controls=[expected_field, actual_field], spacing=10),
                    ft.Row(controls=[sev_select, prio_select, env_field], spacing=10),
                    err_text,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=620,
            height=480,
        )

        create_modal.title = ft.Text("Report New Defect", size=16, weight=ft.FontWeight.BOLD)
        create_modal.content = modal_body
        create_modal.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_create_modal()),
            submit_btn,
        ]
        create_modal.open = True
        if create_modal not in page.overlay:
            page.overlay.append(create_modal)
        page.update()

    def close_create_modal():
        create_modal.open = False
        page.update()

    # Layout Assembly
    filter_bar = ft.Container(
        content=ft.Row(
            controls=[
                project_dropdown,
                status_dropdown,
                severity_dropdown,
                search_input,
                ft.IconButton(
                    icon=ft.Icons.SEARCH, tooltip="Filter", on_click=lambda _: on_filter_change()
                ),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    text="Report Defect",
                    icon=ft.Icons.ADD,
                    bgcolor=Colors.ACTION_MINT,
                    color=Colors.SURFACE_CARD,
                    height=38,
                    on_click=lambda _: open_create_defect_modal(),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.CARD,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )

    pagination_bar = ft.Row(
        controls=[
            pagination_text,
            ft.Row(controls=[prev_btn, next_btn], spacing=4),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    main_column.controls.extend(
        [
            ft.Row(
                controls=[
                    ft.Text(
                        "Defects & Issues Ledger",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, icon_size=18, on_click=lambda _: fetch_issues()
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            filter_bar,
            table_container,
            pagination_bar,
        ]
    )

    load_projects_filter()
    fetch_issues()

    if params and params.get("open_create"):
        open_create_defect_modal()

    return main_column
