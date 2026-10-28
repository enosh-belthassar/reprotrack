"""Severity, Status, and Priority visual badge chips."""

import flet as ft

from frontend.tokens import Colors, Radii, Typography


def build_severity_badge(severity: str) -> ft.Container:
    sev = (severity or "MEDIUM").upper()
    configs = {
        "CRITICAL": (Colors.BADGE_CRITICAL_BG, Colors.BADGE_CRITICAL_TEXT, ft.Icons.ERROR_OUTLINE),
        "HIGH": (Colors.BADGE_HIGH_BG, Colors.BADGE_HIGH_TEXT, ft.Icons.WARNING_AMBER_OUTLINED),
        "MEDIUM": (Colors.BADGE_MEDIUM_BG, Colors.BADGE_MEDIUM_TEXT, ft.Icons.INFO_OUTLINE),
        "LOW": (Colors.BADGE_LOW_BG, Colors.BADGE_LOW_TEXT, ft.Icons.CIRCLE_OUTLINED),
    }
    bg, fg, icon_data = configs.get(
        sev, (Colors.BADGE_MEDIUM_BG, Colors.BADGE_MEDIUM_TEXT, ft.Icons.INFO_OUTLINE)
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon_data, size=11, color=fg),
                ft.Text(
                    sev,
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=fg,
                    font_family=Typography.FONT_MONO,
                ),
            ],
            spacing=3,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=bg,
        border_radius=Radii.BADGE,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )


def build_status_badge(status: str) -> ft.Container:
    stat = (status or "REPORTED").upper()
    configs = {
        "REPORTED": (Colors.BADGE_TRIAGE_BG, Colors.BADGE_TRIAGE_TEXT, "REPORTED"),
        "TRIAGED": (Colors.BADGE_TRIAGE_BG, Colors.BADGE_TRIAGE_TEXT, "TRIAGED"),
        "IN_PROGRESS": (Colors.BADGE_IN_PROGRESS_BG, Colors.BADGE_IN_PROGRESS_TEXT, "IN PROGRESS"),
        "FIXED": (Colors.BADGE_FIXED_BG, Colors.BADGE_FIXED_TEXT, "FIXED"),
        "IN_VERIFICATION": (Colors.BADGE_MEDIUM_BG, Colors.BADGE_MEDIUM_TEXT, "IN VERIFICATION"),
        "CLOSED": (Colors.BADGE_VERIFIED_BG, Colors.BADGE_VERIFIED_TEXT, "CLOSED"),
        "REOPENED": (Colors.BADGE_REOPENED_BG, Colors.BADGE_REOPENED_TEXT, "REOPENED"),
        "WONT_FIX": (Colors.BADGE_WONT_FIX_BG, Colors.BADGE_WONT_FIX_TEXT, "WONT FIX"),
    }
    bg, fg, label = configs.get(stat, (Colors.BADGE_LOW_BG, Colors.BADGE_LOW_TEXT, stat))

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(width=6, height=6, border_radius=3, bgcolor=fg),
                ft.Text(
                    label,
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=fg,
                    font_family=Typography.FONT_MONO,
                ),
            ],
            spacing=4,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=bg,
        border_radius=Radii.BADGE,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )


def build_priority_badge(priority: str) -> ft.Container:
    prio = (priority or "NORMAL").upper()
    fg_map = {
        "URGENT": Colors.ERROR,
        "HIGH": Colors.WARNING,
        "NORMAL": Colors.INFO,
        "LOW": Colors.SECONDARY_TEXT,
    }
    fg = fg_map.get(prio, Colors.SECONDARY_TEXT)
    return ft.Container(
        content=ft.Text(
            prio, size=10, weight=ft.FontWeight.W_600, color=fg, font_family=Typography.FONT_MONO
        ),
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.BADGE,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )
