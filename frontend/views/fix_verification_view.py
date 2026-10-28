"""Fix Verification console for testers and QA leads to verify and close or reopen defects."""

from typing import Any, Dict, Optional

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.badges import build_severity_badge, build_status_badge
from frontend.components.feedback import build_empty_state, build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_fix_verification_view(
    api_client: ReproTrackApiClient,
    page: ft.Page,
    params: Optional[Dict[str, Any]] = None,
) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    selected_issue_id = params.get("issue_id") if params else None
    pending_list_container = ft.Container(width=340)
    inspector_container = ft.Container(expand=True)

    def load_pending_verification():
        pending_list_container.content = build_loading_state("Loading pending fixes...")
        pending_list_container.update()

        try:
            pending_issues = api_client.get_pending_verifications()
        except ApiClientError as err:
            pending_list_container.content = build_error_banner(
                err.message, on_retry=lambda _: load_pending_verification()
            )
            pending_list_container.update()
            return

        if not pending_issues:
            pending_list_container.content = build_empty_state(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                title="No Pending Fixes",
                subtitle="All resolved defects have been verified or none are awaiting QA sign-off.",
            )
            inspector_container.content = ft.Container(
                content=ft.Text(
                    "Select a defect awaiting verification to execute test run.",
                    size=13,
                    color=Colors.SECONDARY_TEXT,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
            pending_list_container.update()
            inspector_container.update()
            return

        nonlocal selected_issue_id
        if not selected_issue_id or not any(i["id"] == selected_issue_id for i in pending_issues):
            selected_issue_id = pending_issues[0]["id"]

        cards = []
        for iss in pending_issues:
            i_id = iss["id"]
            i_key = iss["issue_key"]
            i_title = iss["title"]
            i_stat = iss["status"]
            i_sev = iss["severity"]
            is_selected = i_id == selected_issue_id

            def make_select_handler(target_id: int):
                def handler(_):
                    nonlocal selected_issue_id
                    selected_issue_id = target_id
                    load_pending_verification()

                return handler

            cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        i_key,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        font_family=Typography.FONT_MONO,
                                        color=Colors.INFO,
                                    ),
                                    build_severity_badge(i_sev),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                i_title,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=Colors.MAIN_TEXT,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                controls=[
                                    build_status_badge(i_stat),
                                    ft.Text(
                                        f"Assignee: {iss.get('assignee_name') or 'Unassigned'}",
                                        size=11,
                                        color=Colors.SECONDARY_TEXT,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=6,
                    ),
                    bgcolor=Colors.SURFACE_CARD if not is_selected else Colors.BADGE_MEDIUM_BG,
                    border=ft.border.all(
                        1.5 if is_selected else 1,
                        Colors.ACTION_MINT if is_selected else Colors.BORDER,
                    ),
                    border_radius=Radii.STANDARD,
                    padding=ft.padding.all(12),
                    ink=True,
                    on_click=make_select_handler(i_id),
                )
            )

        pending_list_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Awaiting Verification ({len(pending_issues)})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    ft.Column(controls=cards, spacing=8, scroll=ft.ScrollMode.AUTO, height=580),
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(14),
        )

        # Load selected issue inspector
        load_selected_inspector(selected_issue_id)
        pending_list_container.update()

    def load_selected_inspector(issue_id: int):
        inspector_container.content = build_loading_state("Loading defect test context...")
        inspector_container.update()

        try:
            issue = api_client.get_issue(issue_id)
            history_runs = api_client.list_issue_verifications(issue_id)
        except ApiClientError as err:
            inspector_container.content = build_error_banner(err.message)
            inspector_container.update()
            return

        key = issue["issue_key"]
        title = issue["title"]
        steps = issue.get("steps_to_reproduce", "")
        expected = issue.get("expected_result", "")
        actual = issue.get("actual_result", "")
        assignee_id = issue.get("assignee_id")
        current_uid = state.current_user.get("id") if state.current_user else None

        # Separation of duties warning if current user is the developer
        is_self_developer = (
            assignee_id is not None and assignee_id == current_uid and not state.is_global_admin
        )

        # Verification form inputs
        version_input = ft.TextField(
            label="Tested Version / Build Tag *",
            hint_text="e.g. v1.4.0-rc2 or commit 7a8f9c",
            height=44,
            text_size=12,
        )

        outcome_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(value="PASS", label="PASS (Verify & Close Defect)"),
                    ft.Radio(value="FAIL", label="FAIL (Reopen Defect with Failure Notes)"),
                ],
                spacing=20,
            ),
            value="PASS",
        )

        notes_input = ft.TextField(
            label="Verification Notes & Evidence *",
            hint_text="Document testing environment, test case steps, execution results, or regression logs...",
            multiline=True,
            min_lines=3,
            max_lines=6,
            text_size=12,
        )

        form_err = ft.Text(value="", color=Colors.ERROR, size=12, visible=False)
        record_btn = ft.ElevatedButton(
            text="Record Verification Run",
            icon=ft.Icons.VERIFIED,
            bgcolor=Colors.ACTION_MINT,
            color=Colors.SURFACE_CARD,
            height=40,
            disabled=is_self_developer,
        )

        def submit_run(_):
            v_val = version_input.value.strip() if version_input.value else ""
            n_val = notes_input.value.strip() if notes_input.value else ""
            r_val = outcome_radio.value

            if not v_val or not n_val:
                form_err.value = "Tested version tag and verification notes are mandatory."
                form_err.visible = True
                form_err.update()
                return

            record_btn.disabled = True
            record_btn.update()

            try:
                run_res = api_client.submit_verification(
                    issue_id=issue_id,
                    result=r_val,
                    test_notes=n_val,
                    tested_version=v_val,
                )
                if state.show_message:
                    state.show_message(
                        f"Verification recorded: {run_res['result']} on {key}", False
                    )
                load_pending_verification()
            except ApiClientError as err:
                form_err.value = err.message
                form_err.visible = True
                record_btn.disabled = False
                form_err.update()
                record_btn.update()

        record_btn.on_click = submit_run

        self_dev_warning = ft.Container()
        if is_self_developer:
            self_dev_warning = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.GAVEL, size=16, color=Colors.WARNING),
                        ft.Text(
                            "Separation of Duties Policy: You are assigned as the developer for this fix. A different tester or administrator must verify this outcome.",
                            size=12,
                            color=Colors.WARNING,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                bgcolor=Colors.BADGE_HIGH_BG,
                border_radius=Radii.STANDARD,
                padding=ft.padding.all(10),
            )

        # Historical Runs
        history_rows = []
        for h in history_runs:
            is_pass = h["result"] == "PASS"
            history_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    h["result"],
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=Colors.SURFACE_CARD,
                                ),
                                bgcolor=Colors.SUCCESS if is_pass else Colors.ERROR,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(ft.Text(h.get("tester_name", ""), size=11)),
                        ft.DataCell(
                            ft.Text(
                                h.get("tested_version", ""),
                                size=11,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                        ft.DataCell(ft.Text(h.get("test_notes", "")[:60], size=11)),
                        ft.DataCell(
                            ft.Text(
                                h.get("created_at", "")[:16].replace("T", " "),
                                size=10,
                                color=Colors.MUTED_TEXT,
                                font_family=Typography.FONT_MONO,
                            )
                        ),
                    ]
                )
            )

        history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("OUTCOME", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("TESTER", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("VERSION", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("NOTES", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("TIMESTAMP", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=history_rows,
            heading_row_color=Colors.SURFACE_LOW,
            column_spacing=12,
        )

        inspector_card = ft.Container(
            content=ft.Column(
                controls=[
                    # Header
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        key,
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        font_family=Typography.FONT_MONO,
                                        color=Colors.PRIMARY_NAVY,
                                    ),
                                    build_status_badge(issue["status"]),
                                    build_severity_badge(issue["severity"]),
                                ],
                                spacing=8,
                            ),
                            ft.OutlinedButton(
                                text="Open Ticket",
                                icon=ft.Icons.OPEN_IN_NEW,
                                height=32,
                                on_click=lambda _: (
                                    state.navigate("issue_details", {"issue_id": issue["id"]})
                                    if state.navigate
                                    else None
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=Colors.MAIN_TEXT),
                    ft.Divider(height=12, color=Colors.BORDER),
                    # Reproduction Context
                    ft.Text(
                        "Reproduction Context",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    ft.Container(
                        content=ft.Text(
                            steps if steps else "No reproduction steps provided.",
                            size=11,
                            font_family=Typography.FONT_MONO,
                        ),
                        bgcolor=Colors.SURFACE_LOW,
                        border_radius=Radii.STANDARD,
                        padding=ft.padding.all(8),
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Expected",
                                            size=10,
                                            weight=ft.FontWeight.BOLD,
                                            color=Colors.SUCCESS,
                                        ),
                                        ft.Text(expected, size=11),
                                    ],
                                    spacing=2,
                                ),
                                bgcolor=Colors.BADGE_VERIFIED_BG,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.all(8),
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Actual",
                                            size=10,
                                            weight=ft.FontWeight.BOLD,
                                            color=Colors.ERROR,
                                        ),
                                        ft.Text(actual, size=11),
                                    ],
                                    spacing=2,
                                ),
                                bgcolor=Colors.BADGE_CRITICAL_BG,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.all(8),
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=16, color=Colors.BORDER),
                    # Verification Action Form
                    ft.Text(
                        "Record Verification Result",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    self_dev_warning,
                    outcome_radio,
                    version_input,
                    notes_input,
                    form_err,
                    record_btn,
                    ft.Divider(height=16, color=Colors.BORDER),
                    # History
                    ft.Text(
                        f"Verification Attempts & Audits ({len(history_runs)})",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    history_table
                    if history_rows
                    else ft.Text(
                        "No prior verification runs recorded.", size=11, color=Colors.MUTED_TEXT
                    ),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(20),
            expand=True,
        )

        inspector_container.content = inspector_card
        inspector_container.update()

    # Layout Row
    workspace_row = ft.Row(
        controls=[
            pending_list_container,
            inspector_container,
        ],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.START,
        spacing=16,
        expand=True,
    )

    main_column.controls.extend(
        [
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Fix Verification Console",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.PRIMARY_NAVY,
                            ),
                            ft.Text(
                                "Rigorous QA audit station: Verify resolved defects on target builds before closing.",
                                size=12,
                                color=Colors.SECONDARY_TEXT,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Refresh Queue",
                        on_click=lambda _: load_pending_verification(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            workspace_row,
        ]
    )

    load_pending_verification()
    return main_column
