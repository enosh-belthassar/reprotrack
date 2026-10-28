"""Login view for ReproTrack."""

from typing import Callable

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_login_view(
    api_client: ReproTrackApiClient,
    on_login_success: Callable[[], None],
) -> ft.Container:
    ident_input = ft.TextField(
        label="Email or Username",
        hint_text="e.g. admin@demo.local",
        border_color=Colors.BORDER,
        focused_border_color=Colors.ACTION_MINT,
        height=48,
        text_size=14,
        autofocus=True,
    )

    pwd_input = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        border_color=Colors.BORDER,
        focused_border_color=Colors.ACTION_MINT,
        height=48,
        text_size=14,
    )

    error_text = ft.Text(
        value="",
        color=Colors.ERROR,
        size=12,
        visible=False,
    )

    login_btn = ft.ElevatedButton(
        text="Sign In to ReproTrack",
        bgcolor=Colors.PRIMARY_NAVY,
        color=Colors.ON_NAVY_TEXT,
        height=42,
        width=360,
    )

    loading_ring = ft.ProgressRing(
        width=20, height=20, stroke_width=2, color=Colors.ACTION_MINT, visible=False
    )

    def handle_login(_):
        ident = ident_input.value.strip() if ident_input.value else ""
        pwd = pwd_input.value if pwd_input.value else ""

        if not ident or not pwd:
            error_text.value = "Please enter both identifier and password."
            error_text.visible = True
            error_text.update()
            return

        # Double-submit guard & loading state
        login_btn.disabled = True
        loading_ring.visible = True
        error_text.visible = False
        login_btn.update()
        loading_ring.update()
        error_text.update()

        try:
            res = api_client.login(ident, pwd)
            state.token = res["token"]
            state.current_user = res["user"]
            on_login_success()
        except ApiClientError as err:
            error_text.value = err.message
            error_text.visible = True
            login_btn.disabled = False
            loading_ring.visible = False
            login_btn.update()
            loading_ring.update()
            error_text.update()
        except Exception as exc:
            error_text.value = f"Connection error: {exc}"
            error_text.visible = True
            login_btn.disabled = False
            loading_ring.visible = False
            login_btn.update()
            loading_ring.update()
            error_text.update()

    login_btn.on_click = handle_login

    card = ft.Container(
        content=ft.Column(
            controls=[
                # Brand Header
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BUG_REPORT, size=32, color=Colors.ACTION_MINT),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "REPROTRACK",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=Colors.PRIMARY_NAVY,
                                    font_family=Typography.FONT_MONO,
                                ),
                                ft.Text(
                                    "Bug Reporting, Testing & Fix Verification",
                                    size=11,
                                    color=Colors.SECONDARY_TEXT,
                                ),
                            ],
                            spacing=1,
                        ),
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=24, color="transparent"),
                ident_input,
                pwd_input,
                error_text,
                ft.Container(height=8),
                login_btn,
                ft.Row(controls=[loading_ring], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=16, color=Colors.BORDER),
                # Local evaluation note
                ft.Container(
                    content=ft.Text(
                        "Local Environment: Sign in with your bootstrapped administrator or project credentials.",
                        size=11,
                        color=Colors.SECONDARY_TEXT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=8),
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=420,
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.CARD,
        padding=ft.padding.all(32),
    )

    return ft.Container(
        content=card,
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=Colors.CANVAS_BASE,
    )
