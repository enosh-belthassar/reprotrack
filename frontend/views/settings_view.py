"""Settings and safe system diagnostics view."""

import time

import flet as ft

from frontend.api_client import ApiClientError, ReproTrackApiClient
from frontend.components.feedback import build_error_banner, build_loading_state
from frontend.state import state
from frontend.tokens import Colors, Radii, Typography


def build_settings_view(api_client: ReproTrackApiClient, page: ft.Page) -> ft.Control:
    main_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    diagnostics_container = ft.Container(expand=True)
    health_result_text = ft.Text(
        "Click 'Run Live Health Check' to test connection.", size=12, color=Colors.SECONDARY_TEXT
    )

    def load_diagnostics():
        diagnostics_container.content = build_loading_state("Reading safe diagnostics...")
        diagnostics_container.update()

        try:
            diag = api_client.get_system_diagnostics()
        except ApiClientError as err:
            diagnostics_container.content = build_error_banner(
                err.message, on_retry=lambda _: load_diagnostics()
            )
            diagnostics_container.update()
            return

        diag_items = [
            ("Environment (APP_ENV)", diag.get("app_env", "")),
            ("Database Engine", diag.get("database_type", "")),
            ("Session TTL", f"{diag.get('token_ttl_hours', 8)} hours"),
            ("Login Throttling Window", f"{diag.get('login_window_minutes', 15)} minutes"),
            ("Max Login Failures", f"{diag.get('login_max_failures', 5)} attempts"),
            ("Max Page Size", str(diag.get("max_page_size", 100))),
            ("Frontend API Base URL", diag.get("reprotrack_api_url", "")),
            ("CORS Allowed Origins Count", str(diag.get("cors_configured_origins_count", 0))),
        ]

        rows = []
        for lbl, val in diag_items:
            rows.append(
                ft.Row(
                    controls=[
                        ft.Text(lbl, size=12, color=Colors.SECONDARY_TEXT, width=220),
                        ft.Text(
                            val,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=Colors.MAIN_TEXT,
                            font_family=Typography.FONT_MONO,
                        ),
                    ],
                    spacing=12,
                )
            )

        diag_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Runtime Configuration (Safe Diagnostics)",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.PRIMARY_NAVY,
                    ),
                    ft.Text(
                        "Validated configuration parameters. Database credentials, tokens, and secret keys are never disclosed.",
                        size=11,
                        color=Colors.MUTED_TEXT,
                    ),
                    ft.Divider(height=12, color=Colors.BORDER),
                    ft.Column(controls=rows, spacing=8),
                ],
                spacing=8,
            ),
            bgcolor=Colors.SURFACE_CARD,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Radii.CARD,
            padding=ft.padding.all(20),
            width=580,
        )

        diagnostics_container.content = diag_card
        diagnostics_container.update()

    def run_health_check(_):
        health_result_text.value = "Pinging /system/health..."
        health_result_text.color = Colors.INFO
        health_result_text.update()

        t0 = time.perf_counter()
        try:
            h = api_client.get_system_health()
            lat_ms = (time.perf_counter() - t0) * 1000.0
            db_conn = "Connected" if h.get("database_connected") else "Degraded"
            health_result_text.value = f"Status: {h.get('status', 'OK')} | Database: {db_conn} | Version: {h.get('version', '')} | Latency: {lat_ms:.1f}ms"
            health_result_text.color = Colors.SUCCESS
        except Exception as exc:
            health_result_text.value = f"Health check failed: {exc}"
            health_result_text.color = Colors.ERROR
        health_result_text.update()

    # User Profile Card
    u = state.current_user or {}
    user_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Active Session", size=13, weight=ft.FontWeight.BOLD, color=Colors.PRIMARY_NAVY
                ),
                ft.Divider(height=12, color=Colors.BORDER),
                ft.Row(
                    controls=[
                        ft.Text("Display Name:", size=12, color=Colors.SECONDARY_TEXT, width=120),
                        ft.Text(u.get("display_name", ""), size=12, weight=ft.FontWeight.W_600),
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.Text("Email:", size=12, color=Colors.SECONDARY_TEXT, width=120),
                        ft.Text(u.get("email_normalized", ""), size=12, weight=ft.FontWeight.W_600),
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.Text("Global Role:", size=12, color=Colors.SECONDARY_TEXT, width=120),
                        ft.Text(
                            u.get("global_role", ""),
                            size=12,
                            weight=ft.FontWeight.W_600,
                            font_family=Typography.FONT_MONO,
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.Text("User ID:", size=12, color=Colors.SECONDARY_TEXT, width=120),
                        ft.Text(
                            str(u.get("id", "")),
                            size=12,
                            weight=ft.FontWeight.W_600,
                            font_family=Typography.FONT_MONO,
                        ),
                    ]
                ),
            ],
            spacing=8,
        ),
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.CARD,
        padding=ft.padding.all(20),
        width=580,
    )

    # Health Check Card
    health_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "API Connectivity & Health Verification",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=Colors.PRIMARY_NAVY,
                ),
                ft.Text(
                    "Live HTTP roundtrip verification against ReproTrack backend service.",
                    size=11,
                    color=Colors.MUTED_TEXT,
                ),
                ft.Divider(height=12, color=Colors.BORDER),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            text="Run Live Health Check",
                            icon=ft.Icons.NETWORK_CHECK,
                            bgcolor=Colors.PRIMARY_NAVY,
                            color=Colors.ON_NAVY_TEXT,
                            height=36,
                            on_click=run_health_check,
                        ),
                    ],
                ),
                health_result_text,
            ],
            spacing=8,
        ),
        bgcolor=Colors.SURFACE_CARD,
        border=ft.border.all(1, Colors.BORDER),
        border_radius=Radii.CARD,
        padding=ft.padding.all(20),
        width=580,
    )

    main_column.controls.extend(
        [
            ft.Text(
                "System Settings & Diagnostics",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=Colors.PRIMARY_NAVY,
            ),
            diagnostics_container,
            ft.Divider(height=12, color="transparent"),
            user_card,
            ft.Divider(height=12, color="transparent"),
            health_card,
        ]
    )

    load_diagnostics()
    return main_column
