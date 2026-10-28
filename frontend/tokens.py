"""Technical Precision design tokens for ReproTrack Flet UI."""


class Colors:
    # Core Foundation
    PRIMARY_NAVY = "#15263B"
    SECONDARY_NAVY = "#213B54"
    ACTION_MINT = "#36B78A"
    ACTION_MINT_HOVER = "#2E9D76"

    # Surfaces & Canvas
    CANVAS_BASE = "#F5F7FA"
    SURFACE_CARD = "#FFFFFF"
    SURFACE_LOW = "#F2F4F7"
    SURFACE_HOVER = "#F8FAFC"
    SURFACE_CONTAINER = "#ECEEF1"
    SURFACE_HIGH = "#E6E8EB"

    # Text & Content
    MAIN_TEXT = "#1E293B"
    SECONDARY_TEXT = "#64748B"
    MUTED_TEXT = "#94A3B8"
    ON_NAVY_TEXT = "#FFFFFF"
    ON_NAVY_MUTED = "#A0AEC0"

    # Structural Lines & Borders
    BORDER = "#E2E8F0"
    BORDER_DARK = "#CBD5E1"
    BORDER_FOCUSED = "#36B78A"

    # Status & Semantics
    SUCCESS = "#198754"
    WARNING = "#D99000"
    ERROR = "#DC3545"
    INFO = "#2673C8"

    # Badge Backgrounds (12% opacity tints)
    BADGE_CRITICAL_BG = "#FDE8E8"
    BADGE_CRITICAL_TEXT = "#9B1C1C"
    BADGE_HIGH_BG = "#FEF08A"
    BADGE_HIGH_TEXT = "#854D0E"
    BADGE_MEDIUM_BG = "#E0F2FE"
    BADGE_MEDIUM_TEXT = "#075985"
    BADGE_LOW_BG = "#F1F5F9"
    BADGE_LOW_TEXT = "#475569"

    BADGE_VERIFIED_BG = "#DEF7EC"
    BADGE_VERIFIED_TEXT = "#03543F"
    BADGE_TRIAGE_BG = "#E1EFFE"
    BADGE_TRIAGE_TEXT = "#1E429F"
    BADGE_IN_PROGRESS_BG = "#EDE9FE"
    BADGE_IN_PROGRESS_TEXT = "#5B21B6"
    BADGE_FIXED_BG = "#FEF3C7"
    BADGE_FIXED_TEXT = "#92400E"
    BADGE_REOPENED_BG = "#FEE2E2"
    BADGE_REOPENED_TEXT = "#991B1B"
    BADGE_WONT_FIX_BG = "#F3F4F6"
    BADGE_WONT_FIX_TEXT = "#4B5563"


class Radii:
    STANDARD = 4
    CARD = 8
    MODAL = 8
    BADGE = 4


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Typography:
    FONT_FAMILY = "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif"
    FONT_MONO = "Consolas, 'JetBrains Mono', 'Courier New', monospace"
