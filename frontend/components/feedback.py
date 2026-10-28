"""Loading indicators, empty states, and feedback banners."""

from typing import Any, Callable, Optional

import flet as ft

from frontend.tokens import Colors, Radii


def build_loading_state(message: str = "Loading data from server...") -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=28, height=28, stroke_width=3, color=Colors.ACTION_MINT),
                ft.Text(message, size=13, color=Colors.SECONDARY_TEXT),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.alignment.center,
        expand=True,
        padding=40,
    )


def build_empty_state(
    icon: str = ft.Icons.INBOX_OUTLINED,
    title: str = "No records found",
    subtitle: str = "There is currently no data matching this view.",
    action_text: Optional[str] = None,
    on_action: Optional[Callable[[Any], None]] = None,
) -> ft.Container:
    controls = [
        ft.Icon(icon, size=40, color=Colors.MUTED_TEXT),
        ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=Colors.MAIN_TEXT),
        ft.Text(subtitle, size=13, color=Colors.SECONDARY_TEXT, text_align=ft.TextAlign.CENTER),
    ]
    if action_text and on_action:
        controls.append(
            ft.ElevatedButton(
                text=action_text,
                bgcolor=Colors.ACTION_MINT,
                color=Colors.SURFACE_CARD,
                on_click=on_action,
                height=34,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=controls,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.alignment.center,
        expand=True,
        padding=40,
    )


def build_error_banner(
    message: str,
    on_retry: Optional[Callable[[Any], None]] = None,
) -> ft.Container:
    controls = [
        ft.Icon(ft.Icons.ERROR_OUTLINE, size=18, color=Colors.ERROR),
        ft.Text(message, size=13, color=Colors.ERROR, expand=True),
    ]
    if on_retry:
        controls.append(
            ft.TextButton(
                text="Retry",
                on_click=on_retry,
            )
        )

    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=Colors.BADGE_CRITICAL_BG,
        border=ft.border.all(1, Colors.ERROR),
        border_radius=Radii.STANDARD,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        margin=ft.margin.only(bottom=12),
    )
