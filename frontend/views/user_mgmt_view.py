"""User administration and audit log view (Global Administrator only)."""

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_user_mgmt_view(api_client: ReproTrackApiClient, page: ft.Page) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    if not state.is_global_admin:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=40, color=Colors.ERROR),
                    ft.Text(
                        "Administrator Access Required",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.MAIN_TEXT,
                    ),
                    ft.Text(
                        "Only global administrators can access the user administration console.",
                        size=12,
                        color=Colors.SECONDARY_TEXT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            alignment=ft.alignment.center,
            padding=40,
        )

    users_container = ft.Container(expand=True)
    audit_container = ft.Container(expand=True)

    create_user_dialog = ft.AlertDialog(modal=True)
    edit_user_dialog = ft.AlertDialog(modal=True)
    deactivate_confirm_dialog = ft.AlertDialog(modal=True)

    def load_users():
        users_container.content = build_loading_state("Loading users from server...")
        users_container.update()

        try:
            users_list = api_client.list_users()
            audit_events = api_client.list_audit_events(limit=30)
        except ApiClientError as err:
            users_container.content = build_error_banner(
                err.message, on_retry=lambda _: load_users()
            )
            users_container.update()
            return

        # Users table
        rows = []
        for u in users_list:
            u_id = u["id"]
            u_name = u["display_name"]
            u_email = u["email_normalized"]
            u_role = u["global_role"]
            u_active = u["is_active"]
            u_login = (
                u.get("last_login_at", "")[:16].replace("T", " ")
                if u.get("last_login_at")
                else "Never"
            )

            def make_edit_handler(user_data: dict):
                return lambda _: open_edit_modal(user_data)

            def make_deact_handler(target_id: int, target_name: str):
                return lambda _: open_deactivate_confirm(target_id, target_name)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(u_name, size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(u_email, size=12, color=Colors.SECONDARY_TEXT)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    u_role,
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=Colors.ON_NAVY_TEXT,
                                    font_family=Typography.FONT_MONO,
                                ),
                                bgcolor=Colors.PRIMARY_NAVY
                                if u_role == "GLOBAL_ADMIN"
                                else Colors.SECONDARY_NAVY,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    "Active" if u_active else "Inactive",
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=Colors.SURFACE_CARD,
                                ),
                                bgcolor=Colors.SUCCESS if u_active else Colors.ERROR,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                u_login,
                                size=11,
                                color=Colors.MUTED_TEXT,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_size=16,
                                        tooltip="Edit User",
                                        on_click=make_edit_handler(u),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.PERSON_OFF_OUTLINED,
                                        icon_size=16,
                                        icon_color=Colors.ERROR,
                                        tooltip="Deactivate User",
                                        disabled=not u_active,
                                        on_click=make_deact_handler(u_id, u_name),
                                    ),
                                ],
                                spacing=4,
                            )
                        ),
                    ]
                )
            )

        u_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("NAME", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("EMAIL", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("GLOBAL ROLE", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("STATUS", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("LAST LOGIN (UTC)", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ACTIONS", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=16,
        )

        users_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"Managed Accounts ({len(users_list)})",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.PRIMARY_NAVY,
                            ),
                            ft.ElevatedButton(
                                text="Create User",
                                icon=ft.Icons.PERSON_ADD,
                                bgcolor=Colors.ACTION_MINT,
                                color=Colors.SURFACE_CARD,
                                height=34,
                                on_click=lambda _: open_create_user_modal(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    u_table,
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        # Audit Events Table
        audit_rows = []
        for a in audit_events:
            audit_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                a.get("action", ""),
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                font_family=Typography.FONT_MONO,
                                color=Colors.PRIMARY_NAVY,
                            )
                        ),
                        ft.DataCell(ft.Text(a.get("actor_name", "System"), size=11)),
                        ft.DataCell(
                            ft.Text(
                                f"{a.get('entity_type', '')} #{a.get('entity_id') or ''}",
                                size=11,
                                color=Colors.SECONDARY_TEXT,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                a.get("metadata_json") or "",
                                size=10,
                                font_family=Typography.FONT_MONO,
                                color=Colors.MUTED_TEXT,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                a.get("timestamp", "")[:16].replace("T", " "),
                                size=10,
                                color=Colors.MUTED_TEXT,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                    ]
                )
            )

        audit_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ACTION", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ACTOR", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("TARGET", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("METADATA", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("TIMESTAMP (UTC)", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=audit_rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=16,
        )

        audit_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "System Audit Trail",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    audit_table
                    if audit_rows
                    else ft.Text(
                        "No administrative audit events recorded.", size=11, color=Colors.MUTED_TEXT
                    ),
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        users_container.update()
        audit_container.update()

    # ------------------ Create User Modal ------------------
    def open_create_user_modal():
        name_input = ft.TextField(label="Full Name *", height=44, text_size=12)
        email_input = ft.TextField(label="Email Address *", height=44, text_size=12)
        pwd_input = ft.TextField(
            label="Initial Password (min 8 chars) *",
            password=True,
            can_reveal_password=True,
            height=44,
            text_size=12,
        )
        role_select = ft.Dropdown(
            label="Global Role",
            options=[ft.dropdown.Option("USER"), ft.dropdown.Option("GLOBAL_ADMIN")],
            value="USER",
            height=44,
            text_size=12,
        )
        c_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def save_new_user(_):
            n = name_input.value.strip() if name_input.value else ""
            e = email_input.value.strip() if email_input.value else ""
            p = pwd_input.value if pwd_input.value else ""

            if not n or not e or not p:
                c_err.value = "All fields are required."
                c_err.visible = True
                c_err.update()
                return

            if len(p) < 8:
                c_err.value = "Password must be at least 8 characters long."
                c_err.visible = True
                c_err.update()
                return

            try:
                api_client.create_user(n, e, p, role_select.value)
                create_user_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message(f"User {e} created successfully.", False)
                load_users()
            except ApiClientError as err:
                c_err.value = err.message
                c_err.visible = True
                c_err.update()

        create_user_dialog.title = ft.Text(
            "Create User Account", size=15, weight=ft.FontWeight.BOLD
        )
        create_user_dialog.content = ft.Container(
            content=ft.Column(
                controls=[name_input, email_input, pwd_input, role_select, c_err],
                spacing=10,
                tight=True,
            ),
            width=380,
        )
        create_user_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_create_dialog()),
            ft.ElevatedButton(
                "Create User",
                bgcolor=Colors.PRIMARY_NAVY,
                color=Colors.ON_NAVY_TEXT,
                on_click=save_new_user,
            ),
        ]
        create_user_dialog.open = True
        if create_user_dialog not in page.overlay:
            page.overlay.append(create_user_dialog)
        page.update()

    def close_create_dialog():
        create_user_dialog.open = False
        page.update()

    # ------------------ Edit User Modal ------------------
    def open_edit_modal(u: dict):
        name_input = ft.TextField(
            label="Full Name", value=u["display_name"], height=44, text_size=12
        )
        role_select = ft.Dropdown(
            label="Global Role",
            options=[ft.dropdown.Option("USER"), ft.dropdown.Option("GLOBAL_ADMIN")],
            value=u["global_role"],
            height=44,
            text_size=12,
        )
        e_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def save_edit(_):
            n = name_input.value.strip() if name_input.value else None
            r = role_select.value
            try:
                api_client.update_user(u["id"], display_name=n, global_role=r)
                edit_user_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message("User updated successfully.", False)
                load_users()
            except ApiClientError as err:
                e_err.value = err.message
                e_err.visible = True
                e_err.update()

        edit_user_dialog.title = ft.Text(
            f"Edit User: {u['email_normalized']}", size=15, weight=ft.FontWeight.BOLD
        )
        edit_user_dialog.content = ft.Container(
            content=ft.Column(controls=[name_input, role_select, e_err], spacing=10, tight=True),
            width=360,
        )
        edit_user_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_edit_dialog()),
            ft.ElevatedButton(
                "Save Changes",
                bgcolor=Colors.PRIMARY_NAVY,
                color=Colors.ON_NAVY_TEXT,
                on_click=save_edit,
            ),
        ]
        edit_user_dialog.open = True
        if edit_user_dialog not in page.overlay:
            page.overlay.append(edit_user_dialog)
        page.update()

    def close_edit_dialog():
        edit_user_dialog.open = False
        page.update()

    # ------------------ Deactivate Confirm ------------------
    def open_deactivate_confirm(user_id: int, user_name: str):
        d_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def do_deactivate(_):
            try:
                api_client.deactivate_user(user_id)
                deactivate_confirm_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message(f"User {user_name} deactivated.", False)
                load_users()
            except ApiClientError as err:
                d_err.value = err.message
                d_err.visible = True
                d_err.update()

        deactivate_confirm_dialog.title = ft.Text(
            "Confirm Account Deactivation", size=15, weight=ft.FontWeight.BOLD, color=Colors.ERROR
        )
        deactivate_confirm_dialog.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Are you sure you want to deactivate {user_name}? All active sessions will be terminated immediately.",
                        size=12,
                    ),
                    d_err,
                ],
                spacing=8,
                tight=True,
            ),
            width=380,
        )
        deactivate_confirm_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_deact_dialog()),
            ft.ElevatedButton(
                "Deactivate",
                bgcolor=Colors.ERROR,
                color=Colors.SURFACE_CARD,
                on_click=do_deactivate,
            ),
        ]
        deactivate_confirm_dialog.open = True
        if deactivate_confirm_dialog not in page.overlay:
            page.overlay.append(deactivate_confirm_dialog)
        page.update()

    def close_deact_dialog():
        deactivate_confirm_dialog.open = False
        page.update()

    # Layout Assembly
    main_column.controls.extend(
        [
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(
                                "User & Security Administration",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.PRIMARY_NAVY,
                            ),
                            ft.Text(
                                "Manage global administrator privileges, user credentials, and review immutable audit events.",
                                size=12,
                                color=Colors.SECONDARY_TEXT,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, tooltip="Refresh", on_click=lambda _: load_users()
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            users_container,
            ft.Divider(height=16, color="transparent"),
            audit_container,
        ]
    )

    load_users()
    return main_column
