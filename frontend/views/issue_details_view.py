"""Issue details view with comments, event audit timeline, and transition controls."""

from typing import Any, Dict, Optional

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.badges import (
    build_priority_badge,
    build_severity_badge,
    build_status_badge,
)
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_issue_details_view(
    api_client: ReproTrackApiClient,
    page: ft.Page,
    params: Optional[Dict[str, Any]] = None,
) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    issue_id = params.get("issue_id") if params else None
    if not issue_id:
        return ft.Container(
            content=ft.Text("No issue specified.", color=Colors.ERROR),
            padding=40,
        )

    # Modals
    transition_dialog = ft.AlertDialog(modal=True)
    assign_dialog = ft.AlertDialog(modal=True)

    def load_detail():
        main_column.controls.clear()
        main_column.controls.append(build_loading_state("Loading defect details and timeline..."))
        main_column.update()

        try:
            issue = api_client.get_issue(issue_id)
            comments = api_client.list_issue_comments(issue_id)
            events = api_client.list_issue_events(issue_id)
            verifications = api_client.list_issue_verifications(issue_id)
        except ApiClientError as err:
            main_column.controls.clear()
            main_column.controls.append(
                build_error_banner(err.message, on_retry=lambda _: load_detail())
            )
            main_column.update()
            return

        main_column.controls.clear()

        # 1. Top Navigation & Action Header
        status = issue.get("status", "REPORTED")
        severity = issue.get("severity", "MEDIUM")
        priority = issue.get("priority", "NORMAL")
        key = issue.get("issue_key", "")
        title = issue.get("title", "")
        version = issue.get("version", 1)

        # Transition button logic
        transition_btn = ft.ElevatedButton(
            text="Transition Status",
            icon=ft.Icons.DIRECTIONS_RUN,
            bgcolor=Colors.PRIMARY_NAVY,
            color=Colors.ON_NAVY_TEXT,
            height=36,
            on_click=lambda _: open_transition_modal(issue),
        )

        assign_btn = ft.OutlinedButton(
            text="Assign",
            icon=ft.Icons.PERSON_ADD_ALT_1_OUTLINED,
            height=36,
            on_click=lambda _: open_assign_modal(issue),
        )

        verify_btn = None
        if status in {"FIXED", "IN_VERIFICATION"}:
            verify_btn = ft.ElevatedButton(
                text="Verify Fix",
                icon=ft.Icons.VERIFIED_OUTLINED,
                bgcolor=Colors.ACTION_MINT,
                color=Colors.SURFACE_CARD,
                height=36,
                on_click=lambda _: (
                    state.navigate("verification", {"issue_id": issue["id"]})
                    if state.navigate
                    else None
                ),
            )

        action_controls = [assign_btn, transition_btn]
        if verify_btn:
            action_controls.insert(0, verify_btn)

        header_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_size=20,
                            tooltip="Back to Issues",
                            on_click=lambda _: state.navigate("issues") if state.navigate else None,
                        ),
                        ft.Text(
                            key,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            font_family=Typography.FONT_MONO,
                            color=Colors.PRIMARY_NAVY,
                        ),
                        build_status_badge(status),
                        build_severity_badge(severity),
                        build_priority_badge(priority),
                        ft.Container(
                            content=ft.Text(
                                f"v{version}",
                                size=11,
                                color=Colors.SECONDARY_TEXT,
                                font_family=Typography.FONT_MONO,
                            ),
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            bgcolor=Colors.SURFACE_LOW,
                            border_radius=Radii.STANDARD,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(controls=action_controls, spacing=10),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        title_text = ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=Colors.MAIN_TEXT)

        # 2. Main Content Split: Left (Details & Comments) + Right (Audit & Verifications)
        # --- Left Pane ---
        desc_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Description",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    ft.Text(
                        issue.get("description") or "No description provided.",
                        size=13,
                        color=Colors.MAIN_TEXT,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        steps_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Steps to Reproduce",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    ft.Container(
                        content=ft.Text(
                            issue.get("steps_to_reproduce", ""),
                            size=12,
                            font_family=Typography.FONT_MONO,
                            color=Colors.MAIN_TEXT,
                        ),
                        bgcolor=Colors.SURFACE_LOW,
                        border_radius=Radii.STANDARD,
                        padding=ft.padding.all(12),
                    ),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        results_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Expected vs Actual Results",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Expected Outcome",
                                            size=11,
                                            weight=ft.FontWeight.W_600,
                                            color=Colors.SUCCESS,
                                        ),
                                        ft.Text(
                                            issue.get("expected_result", ""),
                                            size=12,
                                            color=Colors.MAIN_TEXT,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                bgcolor=Colors.BADGE_VERIFIED_BG,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.all(12),
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Actual Outcome",
                                            size=11,
                                            weight=ft.FontWeight.W_600,
                                            color=Colors.ERROR,
                                        ),
                                        ft.Text(
                                            issue.get("actual_result", ""),
                                            size=12,
                                            color=Colors.MAIN_TEXT,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                bgcolor=Colors.BADGE_CRITICAL_BG,
                                border_radius=Radii.STANDARD,
                                padding=ft.padding.all(12),
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        # Comments Section
        comment_input = ft.TextField(
            hint_text="Add an auditable note or investigation update...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            text_size=12,
            expand=True,
        )
        comment_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def submit_comment(_):
            val = comment_input.value.strip() if comment_input.value else ""
            if not val:
                return
            try:
                api_client.add_issue_comment(issue_id, val)
                comment_input.value = ""
                load_detail()
            except ApiClientError as err:
                comment_err.value = err.message
                comment_err.visible = True
                comment_err.update()

        comments_list = []
        if comments:
            for c in comments:
                c_author = c.get("author_name", "User")
                c_time = c.get("created_at", "")[:16].replace("T", " ")
                c_body = c.get("body", "")
                comments_list.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            c_author,
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=Colors.PRIMARY_NAVY,
                                        ),
                                        ft.Text(
                                            c_time,
                                            size=10,
                                            color=Colors.MUTED_TEXT,
                                            font_family=Typography.FONT_MONO,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(c_body, size=12, color=Colors.MAIN_TEXT),
                            ],
                            spacing=4,
                        ),
                        bgcolor=Colors.SURFACE_LOW,
                        border_radius=Radii.STANDARD,
                        padding=ft.padding.all(10),
                    )
                )
        else:
            comments_list.append(
                ft.Text("No comments recorded yet.", size=12, color=Colors.SECONDARY_TEXT)
            )

        comments_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Discussion & Investigation Notes ({len(comments)})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.SECONDARY_TEXT,
                    ),
                    ft.Column(controls=comments_list, spacing=8),
                    ft.Divider(height=12, color=Colors.BORDER),
                    ft.Row(
                        controls=[
                            comment_input,
                            ft.ElevatedButton(
                                "Post Note",
                                bgcolor=Colors.PRIMARY_NAVY,
                                color=Colors.ON_NAVY_TEXT,
                                height=36,
                                on_click=submit_comment,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    comment_err,
                ],
                spacing=10,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        left_column = ft.Column(
            controls=[desc_box, steps_box, results_box, comments_box],
            spacing=16,
            expand=3,
        )

        # --- Right Pane: Metadata & Audit Events ---
        meta_items = [
            ("Project", f"{issue.get('project_key', '')} ({issue.get('project_name', '')})"),
            ("Reporter", issue.get("reporter_name", "")),
            ("Assignee", issue.get("assignee_name") or "Unassigned"),
            ("Environment", issue.get("environment") or "Not specified"),
            ("Created (UTC)", issue.get("created_at", "")[:16].replace("T", " ")),
            (
                "Resolved (UTC)",
                issue.get("resolved_at", "")[:16].replace("T", " ")
                if issue.get("resolved_at")
                else "Pending fix",
            ),
            (
                "Closed (UTC)",
                issue.get("closed_at", "")[:16].replace("T", " ")
                if issue.get("closed_at")
                else "Open",
            ),
        ]

        meta_rows = []
        for k_lbl, v_lbl in meta_items:
            meta_rows.append(
                ft.Row(
                    controls=[
                        ft.Text(k_lbl, size=11, color=Colors.SECONDARY_TEXT, width=100),
                        ft.Text(
                            v_lbl,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=Colors.MAIN_TEXT,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                )
            )

        meta_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Defect Attributes",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    ft.Column(controls=meta_rows, spacing=8),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        # Audit History Timeline
        timeline_items = []
        if events:
            for ev in events:
                e_type = ev.get("event_type", "")
                e_actor = ev.get("actor_name", "System")
                e_time = ev.get("created_at", "")[:16].replace("T", " ")
                e_detail = ev.get("details") or ""
                old_v = ev.get("old_value") or ""
                new_v = ev.get("new_value") or ""

                change_str = f"{old_v} -> {new_v}" if (old_v or new_v) else e_detail

                timeline_items.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            e_type,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=Colors.PRIMARY_NAVY,
                                            font_family=Typography.FONT_MONO,
                                        ),
                                        ft.Text(
                                            e_time,
                                            size=10,
                                            color=Colors.MUTED_TEXT,
                                            font_family=Typography.FONT_MONO,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(f"by {e_actor}", size=11, color=Colors.SECONDARY_TEXT),
                                ft.Text(change_str, size=11, color=Colors.MAIN_TEXT)
                                if change_str
                                else ft.Container(),
                            ],
                            spacing=2,
                        ),
                        bgcolor=Colors.SURFACE_LOW,
                        border_radius=Radii.STANDARD,
                        padding=ft.padding.all(8),
                    )
                )

        timeline_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Immutable Audit Trail ({len(events)})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    ft.Column(
                        controls=timeline_items, spacing=6, scroll=ft.ScrollMode.AUTO, height=260
                    ),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        # Verification Runs Card
        verif_items = []
        if verifications:
            for vr in verifications:
                res_pass = vr.get("result") == "PASS"
                verif_items.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            content=ft.Text(
                                                vr.get("result", ""),
                                                size=10,
                                                weight=ft.FontWeight.BOLD,
                                                color=Colors.SURFACE_CARD,
                                            ),
                                            bgcolor=Colors.SUCCESS if res_pass else Colors.ERROR,
                                            border_radius=Radii.STANDARD,
                                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        ),
                                        ft.Text(
                                            f"Version: {vr.get('tested_version', '')}",
                                            size=11,
                                            font_family=Typography.FONT_MONO,
                                            color=Colors.SECONDARY_TEXT,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(
                                    f"Tester: {vr.get('tester_name', '')}",
                                    size=11,
                                    color=Colors.SECONDARY_TEXT,
                                ),
                                ft.Text(
                                    f"Notes: {vr.get('test_notes', '')}",
                                    size=11,
                                    color=Colors.MAIN_TEXT,
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=Colors.SURFACE_LOW,
                        border_radius=Radii.STANDARD,
                        padding=ft.padding.all(8),
                    )
                )
        else:
            verif_items.append(
                ft.Text("No verification runs executed yet.", size=12, color=Colors.SECONDARY_TEXT)
            )

        verif_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Fix Verifications ({len(verifications)})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Divider(height=8, color=Colors.BORDER),
                    ft.Column(controls=verif_items, spacing=6),
                ],
                spacing=6,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(16),
        )

        right_column = ft.Column(
            controls=[meta_card, timeline_card, verif_card],
            spacing=16,
            expand=2,
        )

        split_row = ft.Row(
            controls=[left_column, right_column],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=16,
        )

        main_column.controls.extend(
            [
                header_row,
                title_text,
                ft.Divider(height=12, color=Colors.BORDER),
                split_row,
            ]
        )
        main_column.update()

    # ------------------ Transition Modal ------------------
    def open_transition_modal(issue: dict):
        curr_status = issue["status"]
        # Transition map
        options_map = {
            "REPORTED": [("TRIAGED", "Triage Defect")],
            "TRIAGED": [("IN_PROGRESS", "Start Fix Progress"), ("WONT_FIX", "Mark as Won't Fix")],
            "IN_PROGRESS": [("FIXED", "Mark Fix Ready")],
            "FIXED": [("IN_VERIFICATION", "Send to Verification")],
            "IN_VERIFICATION": [],  # Must be done via Fix Verification console
            "REOPENED": [("IN_PROGRESS", "Resume Progress")],
            "WONT_FIX": [("TRIAGED", "Re-triage Issue")],
            "CLOSED": [("REOPENED", "Reopen Defect")],
        }

        choices = options_map.get(curr_status, [])
        if not choices:
            if curr_status == "IN_VERIFICATION":
                if state.show_message:
                    state.show_message(
                        "Issues in verification must be transitioned by recording a PASS or FAIL in Fix Verification console.",
                        True,
                    )
            else:
                if state.show_message:
                    state.show_message(
                        f"No direct transitions available from status {curr_status}.", True
                    )
            return

        target_dropdown = ft.Dropdown(
            label="Target Status *",
            options=[ft.dropdown.Option(val, lbl) for val, lbl in choices],
            value=choices[0][0],
            height=44,
            text_size=12,
        )

        reason_field = ft.TextField(
            label="Transition Reason / Context",
            hint_text="Mandatory for WONT_FIX and reopening closed issues",
            multiline=True,
            min_lines=2,
            max_lines=3,
            text_size=12,
        )

        t_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def do_transition(_):
            new_st = target_dropdown.value
            r_val = reason_field.value.strip() if reason_field.value else None

            try:
                api_client.transition_issue(
                    issue_id=issue["id"],
                    new_status=new_st,
                    version=issue["version"],
                    reason=r_val,
                )
                transition_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message(f"Issue transitioned to {new_st}", False)
                load_detail()
            except ApiClientError as err:
                t_err.value = err.message
                t_err.visible = True
                t_err.update()

        transition_dialog.title = ft.Text(
            f"Transition Status: {issue['issue_key']} ({curr_status})",
            size=15,
            weight=ft.FontWeight.BOLD,
        )
        transition_dialog.content = ft.Container(
            content=ft.Column(
                controls=[target_dropdown, reason_field, t_err],
                spacing=10,
                tight=True,
            ),
            width=420,
        )
        transition_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_transition_dialog()),
            ft.ElevatedButton(
                "Apply Transition",
                bgcolor=Colors.PRIMARY_NAVY,
                color=Colors.ON_NAVY_TEXT,
                on_click=do_transition,
            ),
        ]
        transition_dialog.open = True
        if transition_dialog not in page.overlay:
            page.overlay.append(transition_dialog)
        page.update()

    def close_transition_dialog():
        transition_dialog.open = False
        page.update()

    # ------------------ Assign Modal ------------------
    def open_assign_modal(issue: dict):
        proj_id = issue["project_id"]
        members = []
        try:
            members = api_client.list_project_members(proj_id)
        except Exception:
            pass

        assignee_options = [ft.dropdown.Option("", "Unassigned")]
        for m in members:
            assignee_options.append(
                ft.dropdown.Option(str(m["user_id"]), f"{m['user_name']} ({m['role']})")
            )

        assignee_select = ft.Dropdown(
            label="Assignee",
            options=assignee_options,
            value=str(issue.get("assignee_id") or ""),
            height=44,
            text_size=12,
        )
        a_err = ft.Text(value="", color=Colors.ERROR, size=11, visible=False)

        def do_assign(_):
            val = assignee_select.value
            target_uid = int(val) if val else None

            try:
                api_client.assign_issue(
                    issue_id=issue["id"],
                    assignee_id=target_uid,
                    version=issue["version"],
                )
                assign_dialog.open = False
                page.update()
                if state.show_message:
                    state.show_message("Assignee updated successfully.", False)
                load_detail()
            except ApiClientError as err:
                a_err.value = err.message
                a_err.visible = True
                a_err.update()

        assign_dialog.title = ft.Text(
            f"Assign Issue: {issue['issue_key']}", size=15, weight=ft.FontWeight.BOLD
        )
        assign_dialog.content = ft.Container(
            content=ft.Column(controls=[assignee_select, a_err], spacing=10, tight=True),
            width=360,
        )
        assign_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda _: close_assign_dialog()),
            ft.ElevatedButton(
                "Save Assignee",
                bgcolor=Colors.PRIMARY_NAVY,
                color=Colors.ON_NAVY_TEXT,
                on_click=do_assign,
            ),
        ]
        assign_dialog.open = True
        if assign_dialog not in page.overlay:
            page.overlay.append(assign_dialog)
        page.update()

    def close_assign_dialog():
        assign_dialog.open = False
        page.update()

    load_detail()
    return main_column
