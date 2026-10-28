"""Projects and membership management view."""

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.feedback import build_empty_state, build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_projects_view(api_client: ReproTrackApiClient, page: ft.Page) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=20)

    # Dialog references
    create_dialog = ft.AlertDialog(modal=True)
    members_dialog = ft.AlertDialog(modal=True)

    def load_projects():
        main_column.controls.clear()
        main_column.controls.append(build_loading_state("Loading projects..."))
        main_column.update()

        try:
            projects = api_client.list_projects()
        except ApiClientError as err:
            main_column.controls.clear()
            main_column.controls.append(
                build_error_banner(err.message, on_retry=lambda _: load_projects())
            )
            main_column.update()
            return

        main_column.controls.clear()

        # Header with Create Button
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Projects & Workspaces",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY_NAVY,
                        ),
                        ft.Text(
                            "Manage isolated defect workspaces, issue counters, and team access permissions.",
                            size=12,
                            color=Colors.SECONDARY_TEXT,
                        ),
                    ],
                    spacing=2,
                ),
                ft.ElevatedButton(
                    text="New Project",
                    icon=ft.Icons.ADD,
                    bgcolor=Colors.ACTION_MINT,
                    color=Colors.SURFACE_CARD,
                    height=36,
                    on_click=lambda _: open_create_modal(),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        main_column.controls.append(header)

        if not projects:
            main_column.controls.append(
                build_empty_state(
                    icon=ft.Icons.FOLDER_OFF_OUTLINED,
                    title="No accessible projects",
                    subtitle="You are not currently a member of any active projects.",
                    action_text="Create Project",
                    on_action=lambda _: open_create_modal(),
                )
            )
            main_column.update()
            return

        # Build Project Cards
        grid = ft.Row(wrap=True, spacing=16)
        for p in projects:
            p_id = p["id"]
            p_key = p["key"]
            p_name = p["name"]
            p_desc = p.get("description", "")
            p_issues = p.get("issue_count", 0)
            p_role = p.get("my_role", "MEMBER")

            is_active_proj = state.active_project_id == p_id

            def make_set_active_handler(proj_id: int, proj_key: str, proj_name: str):
                def handler(_):
                    state.active_project_id = proj_id
                    state.active_project_key = proj_key
                    state.active_project_name = proj_name
                    if state.show_message:
                        state.show_message(
                            f"Active project switched to [{proj_key}] {proj_name}", False
                        )
                    load_projects()

                return handler

            def make_manage_members_handler(proj_id: int, proj_key: str, proj_name: str):
                return lambda _: open_members_modal(proj_id, proj_key, proj_name)

            card = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(
                                        p_key,
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=Colors.ON_NAVY_TEXT,
                                        font_family=Typography.FONT_MONO,
                                    ),
                                    bgcolor=Colors.PRIMARY_NAVY,
                                    border_radius=Radii.STANDARD,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        p_role,
                                        size=10,
                                        weight=ft.FontWeight.W_600,
                                        color=Colors.SECONDARY_TEXT,
                                        font_family=Typography.FONT_MONO,
                                    ),
                                    bgcolor=Colors.SURFACE_LOW,
                                    border_radius=Radii.STANDARD,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(p_name, size=15, weight=ft.FontWeight.BOLD, color=Colors.MAIN_TEXT),
                        ft.Text(
                            p_desc if p_desc else "No description provided.",
                            size=12,
                            color=Colors.SECONDARY_TEXT,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Divider(height=12, color=Colors.BORDER),
                        ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.BUG_REPORT_OUTLINED,
                                            size=14,
                                            color=Colors.SECONDARY_TEXT,
                                        ),
                                        ft.Text(
                                            f"{p_issues} issues",
                                            size=12,
                                            color=Colors.SECONDARY_TEXT,
                                            font_family=Typography.FONT_MONO,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.GROUP_OUTLINED,
                                            icon_size=16,
                                            tooltip="Manage Team Members",
                                            on_click=make_manage_members_handler(
                                                p_id, p_key, p_name
                                            ),
                                        ),
                                        ft.OutlinedButton(
                                            text="Active" if is_active_proj else "Select",
                                            icon=ft.Icons.CHECK if is_active_proj else None,
                                            height=28,
                                            on_click=make_set_active_handler(p_id, p_key, p_name),
                                        ),
                                    ],
                                    spacing=6,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=8,
                ),
                width=340,
                bgcolor=Colors.SURFACE_CARD,
                border=ft.border.all(
                    2 if is_active_proj else 1,
                    Colors.ACTION_MINT if is_active_proj else Colors.BORDER,
                ),
                border_radius=Radii.CARD,
                padding=ft.padding.all(18),
            )
            grid.controls.append(card)

        main_column.controls.append(grid)
        main_column.update()

    # ------------------ Create Project Modal ------------------
    def open_create_modal():
        key_input = ft.TextField(
            label="Project Key (e.g. RT)", max_length=10, text_size=13, height=44
        )
        name_input = ft.TextField(label="Project Name", max_length=100, text_size=13, height=44)
        desc_input = ft.TextField(
            label="Description", multiline=True, min_lines=2, max_lines=4, text_size=13
        )
        modal_err = ft.Text(value="", color=Colors.ERROR, size=12, visible=False)

        def save_project(_):
            k = key_input.value.strip().upper() if key_input.value else ""
            n = name_input.value.strip() if name_input.value else ""
            d = desc_input.value.strip() if desc_input.value else ""

            if not k or not n:
                modal_err.value = "Project key and name are required."
                modal_err.visible = True
                modal_err.update()
                return

            try:
                new_proj = api_client.create_project(k, n, d)
                create_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message(f"Project '{new_proj['key']}' created successfully.", False)
                load_projects()
            except ApiClientError as err:
                modal_err.value = err.message
                modal_err.visible = True
                modal_err.update()

        create_dialog.title = ft.Text("Create New Project", size=16, weight=ft.FontWeight.BOLD)
        create_dialog.content = ft.Container(
            content=ft.Column(
                controls=[key_input, name_input, desc_input, modal_err],
                spacing=12,
                tight=True,
            ),
            width=400,
        )
        create_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_create_dialog()),
            ft.ElevatedButton(
                "Create",
                bgcolor=Colors.PRIMARY_NAVY,
                color=Colors.ON_NAVY_TEXT,
                on_click=save_project,
            ),
        ]
        create_dialog.open = True
        if create_dialog not in page.overlay:
            page.overlay.append(create_dialog)
        page.update()

    def close_create_dialog():
        create_dialog.open = False
        page.update()

    # ------------------ Members Modal ------------------
    def open_members_modal(proj_id: int, proj_key: str, proj_name: str):
        members_content = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        user_id_input = ft.TextField(label="User ID", width=120, height=40, text_size=12)
        role_dropdown = ft.Dropdown(
            label="Role",
            options=[
                ft.dropdown.Option("PROJECT_ADMIN"),
                ft.dropdown.Option("DEVELOPER"),
                ft.dropdown.Option("TESTER"),
                ft.dropdown.Option("REPORTER"),
                ft.dropdown.Option("VIEWER"),
            ],
            value="DEVELOPER",
            width=160,
            height=40,
            text_size=12,
        )
        add_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def refresh_members():
            members_content.controls.clear()
            try:
                m_list = api_client.list_project_members(proj_id)
            except ApiClientError as err:
                members_content.controls.append(ft.Text(err.message, color=Colors.ERROR, size=12))
                members_content.update()
                return

            rows = []
            for m in m_list:
                uid = m["user_id"]

                def make_remove_handler(target_uid: int):
                    def handler(_):
                        try:
                            api_client.remove_project_member(proj_id, target_uid)
                            refresh_members()
                        except ApiClientError as err:
                            add_err.value = err.message
                            add_err.visible = True
                            add_err.update()

                    return handler

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Text(m.get("user_name", ""), size=12, weight=ft.FontWeight.W_600)
                            ),
                            ft.DataCell(
                                ft.Text(
                                    m.get("user_email", ""), size=11, color=Colors.SECONDARY_TEXT
                                )
                            ),
                            ft.DataCell(
                                ft.Text(
                                    m.get("role", ""), size=11, font_family=Typography.FONT_MONO
                                )
                            ),
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_size=16,
                                    icon_color=Colors.ERROR,
                                    tooltip="Remove Member",
                                    on_click=make_remove_handler(uid),
                                )
                            ),
                        ]
                    )
                )

            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("NAME", size=10, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("EMAIL", size=10, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("ROLE", size=10, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("ACTION", size=10, weight=ft.FontWeight.BOLD)),
                ],
                rows=rows,
                column_spacing=12,
                heading_row_color=Colors.SURFACE_LOW,
            )
            members_content.controls.append(table)
            members_content.update()

        def add_member(_):
            raw_uid = user_id_input.value.strip() if user_id_input.value else ""
            if not raw_uid or not raw_uid.isdigit():
                add_err.value = "Please enter a valid numeric User ID."
                add_err.visible = True
                add_err.update()
                return

            try:
                api_client.add_project_member(proj_id, int(raw_uid), role_dropdown.value)
                user_id_input.value = ""
                add_err.visible = False
                refresh_members()
            except ApiClientError as err:
                add_err.value = err.message
                add_err.visible = True
                add_err.update()

        add_row = ft.Row(
            controls=[
                user_id_input,
                role_dropdown,
                ft.ElevatedButton(
                    "Add",
                    bgcolor=Colors.ACTION_MINT,
                    color=Colors.SURFACE_CARD,
                    height=36,
                    on_click=add_member,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        modal_body = ft.Container(
            content=ft.Column(
                controls=[
                    add_row,
                    add_err,
                    ft.Divider(height=12, color=Colors.BORDER),
                    members_content,
                ],
                spacing=8,
            ),
            width=500,
            height=340,
        )

        members_dialog.title = ft.Text(
            f"Team Members: [{proj_key}] {proj_name}", size=15, weight=ft.FontWeight.BOLD
        )
        members_dialog.content = modal_body
        members_dialog.actions = [
            ft.TextButton("Close", on_click=lambda _: close_members_dialog()),
        ]
        members_dialog.open = True
        if members_dialog not in page.overlay:
            page.overlay.append(members_dialog)
        page.update()
        refresh_members()

    def close_members_dialog():
        members_dialog.open = False
        page.update()

    load_projects()
    return main_column
