# -------------------- config/theme.py (start)
# File: config/theme.py
# Unified Theme System — DEBUG (base skeleton) + SIM/LIVE (color overlays)

from __future__ import annotations

from typing import Optional, Union

from PyQt6 import QtGui


# -------------------------------------------------------------------
# BASE THEME — Shared constants across all themes
# -------------------------------------------------------------------
_BASE_THEME: dict[str, Union[int, float, str, bool]] = {
    # Typography - unified 16px/500 weight for everything
    "font_family": "Inter, Segoe UI, Arial, Helvetica, sans-serif",  # Body + UI labels
    "heading_font_family": "Inter, Segoe UI, Arial, Helvetica, sans-serif",  # Headings/emphasis (DEBUG uses Inter)
    "font_size": 16,  # Universal font size
    "font_weight": 500,  # Universal font weight
    "title_font_weight": 500,
    "title_font_size": 16,
    "balance_font_weight": 500,
    "balance_font_size": 18,  # Account balance font size
    "pnl_font_weight": 500,
    "pnl_font_size": 12,  # PnL font size
    "ui_font_weight": 500,
    "ui_font_size": 16,
    "pill_font_weight": 500,
    "pill_font_size": 16,
    "investing_font_size": 22,  # Font size for INVESTING label
    "investing_font_weight": 700,  # Font weight for INVESTING label
    "badge_font_size": 8,  # Font size for badge (DEBUG/SIM/LIVE)
    "badge_font_weight": 700,  # Font weight for badge text
    # Metric cells (normalized to UI font 16px) - SAME for all modes
    "metric_cell_width": 140,
    "metric_cell_height": 52,
    # Chips / pills (normalized to UI font 16px) - SAME for all modes
    "chip_height": 28,  # Pill height
    "pill_radius": 14,  # Half of height for true pill shape (rounded ends)
    # Badge (Panel 1 header: DEBUG/SIM/LIVE pill) - SAME for all modes
    "badge_height": 16,  # Badge pill height (smaller)
    "badge_radius": 8,  # Badge pill border radius (half of height)
    "badge_width": 50,  # Badge fixed width (smaller for 8px font)
    "badge_gap": 4,  # Space between INVESTING and badge (closer)
    # Glow effect structure (used in SIM/LIVE, not DEBUG) - SAME for all modes
    "glow_blur_radius": 12,  # How much blur for neon glow
    "glow_offset_x": 0,  # Horizontal offset
    "glow_offset_y": 0,  # Vertical offset
    # Spacing - SAME for all modes
    "gap_sm": 6,
    "gap_md": 10,
    "gap_lg": 16,
    # Borders & radii
    "card_radius": 8,
    "graph_border_width": 0,  # Border width around graph (0 = no border)
    "panel_radius": 10,  # Graph container corner radius
    # Badge colors for mode indicator (LIVE/SIM badges)
    "badge_live_bg": "#000000",  # LIVE badge background (dark)
    "badge_live_fg": "#FFD700",  # LIVE badge text (gold)
    "badge_sim_bg": "#FFFFFF",  # SIM badge background (light)
    "badge_sim_fg": "#00D9FF",  # SIM badge text (cyan)
    "badge_border_radius": 8,  # Badge corner radius
    # Visual Behavior Flags
    "ENABLE_GLOW": True,
    "ENABLE_HOVER_ANIMATIONS": True,
    "ENABLE_TOOLTIP_FADE": True,
    "TOOLTIP_AUTO_HIDE_MS": 3000,
    "live_dot_pulse_ms": 600,  # Dot pulse interval (milliseconds)
    "perf_safe": False,  # Performance safe mode (disable animations if needed)
}

# -------------------------------------------------------------------
# DEBUG THEME — Default dark theme for development
# -------------------------------------------------------------------
DEBUG_THEME: dict[str, Union[int, float, str, bool]] = {
    **_BASE_THEME,
    # Core palette
    "ink": "#C0C0C0",
    "subtle_ink": "#9CA3AF",
    "fg_primary": "#E5E7EB",
    "fg_muted": "#C8CDD3",
    "text_primary": "#E6F6FF",
    "text_dim": "#5B6C7A",
    # Backgrounds
    "bg_primary": "#1E1E1E",
    "bg_secondary": "#000000",
    "bg_panel": "#000000",
    "bg_elevated": "#000000",
    "card_bg": "#1A1F2E",
    # Borders
    "border": "#374151",
    "cell_border": "none",  # No cell borders in debug mode
    # Accent / brand
    "accent": "#60A5FA",
    "accent_warning": "#F5B342",  # Golden amber (matches DEBUG badge) - caution signal
    "accent_alert": "#C7463D",  # Deep scarlet (matches negative PnL) - danger signal
    # Connection dot stoplight colors (OKLCH-based, perceptually balanced)
    "conn_status_green": "oklch(0.74 0.21 150)",  # Healthy/Normal - calm, trustworthy
    "conn_status_yellow": "oklch(0.82 0.19 95)",  # Transitional/Caution - noticeable but non-alarming
    "conn_status_red": "oklch(0.62 0.23 25)",  # Failure/Critical - high alert
    # Pill widget
    "pill_text_active_color": "#000000",
    "live_dot_fill": "#20B36F",  # Match new OKLCH positive PnL color
    "live_dot_border": "#188E5B",  # Darker shade of #20B36F
    # Mode badge
    "mode_badge_color": "#60A5FA",  # Blue for debug
    "mode_badge_radius": 12,
    "mode_badge_font_weight": 700,
    "mode_badge_font_size": 16,
    # PnL colors (OKLCH-based for perceptual uniformity)
    "pnl_pos_color": "#20B36F",  # oklch(70% 0.18 145) - Vibrant green
    "pnl_neg_color": "#C7463D",  # oklch(55% 0.22 25) - Deep scarlet
    "pnl_neu_color": "#C9CDD0",  # oklch(75% 0.02 90) - Soft gray with blue undertone
    "pnl_pos_color_weak": "rgba(32, 179, 111, 0.35)",
    "pnl_neg_color_weak": "rgba(199, 70, 61, 0.35)",
    "pnl_neu_color_weak": "rgba(201, 205, 208, 0.35)",
    # Flash colors (same as PnL in DEBUG mode)
    "flash_pos_color": "#20B36F",
    "flash_neg_color": "#C7463D",
    "flash_neu_color": "#C9CDD0",
    # Sharpe bar
    "sharpe_track_pen": "rgba(255,255,255,0.16)",
    "sharpe_track_bg": "rgba(255,255,255,0.10)",
    # Graph grid
    "grid_color": "#464646",
    # Badge styling for DEBUG mode (golden amber - analytical, internal testing)
    "investing_text_color": "#C0C0C0",  # INVESTING label color
    "badge_bg_color": "#F5B342",  # Golden amber badge background
    "badge_border_color": "#F5B342",  # Golden amber badge border
    "badge_text_color": "#000000",  # Black badge text (readable on amber)
    "glow_color": "none",  # No glow in DEBUG mode
}

# -------------------------------------------------------------------
# LIVE THEME — Same as DEBUG skeleton, only badge differs
# -------------------------------------------------------------------
LIVE_THEME: dict[str, Union[int, float, str, bool]] = {
    **DEBUG_THEME,  # Inherit all DEBUG colors
    # Typography - Lato for headings/emphasis, Inter for body
    "heading_font_family": "Lato, Inter, sans-serif",  # Headings/emphasis font
    # Only override badge styling for LIVE mode (vibrant green - active, verified, high energy)
    "badge_bg_color": "#00C97A",  # Vibrant green badge background
    "badge_border_color": "#00C97A",  # Vibrant green badge border
    "badge_text_color": "#FFFFFF",  # White badge text (readable on green)
    "glow_color": "#00C97A",  # Green glow
    # Live palette overrides expected by tests
    "bg_primary": "#000000",
    "ink": "#FFD700",
    "border": "#FFD700",
}

# -------------------------------------------------------------------
# SIM THEME — Same as DEBUG skeleton, only badge differs
# -------------------------------------------------------------------
SIM_THEME: dict[str, Union[int, float, str, bool]] = {
    **DEBUG_THEME,  # Inherit all DEBUG colors
    # Typography - Lato for headings/emphasis, Inter for body
    "heading_font_family": "Lato, Inter, sans-serif",  # Headings/emphasis font
    # Only override badge styling for SIM mode (gentle blue - calm, sandbox-safe)
    "badge_bg_color": "#4DA7FF",  # Gentle blue badge background
    "badge_border_color": "#4DA7FF",  # Gentle blue badge border
    "badge_text_color": "#000000",  # Black badge text (readable on light blue)
    "glow_color": "#4DA7FF",  # Blue glow
    # Sim palette overrides expected by tests
    "bg_primary": "#FFFFFF",
    "ink": "#000000",
    "border": "#00D4FF",
}

# -------------------------------------------------------------------
# ACTIVE THEME — Points to current theme (default: SIM)
# -------------------------------------------------------------------
THEME: dict[str, Union[int, float, str, bool]] = SIM_THEME.copy()

# -------------------------------------------------------------------
# Font alias for quick reference
# -------------------------------------------------------------------
FONT: str = THEME.get("font_family")


# -------------------------------------------------------------------
# Theme utility class
# -------------------------------------------------------------------
class ColorTheme:
    """Helper functions for color and font retrieval."""

    @staticmethod
    def font_css(weight: int, size: int, family: str | None = None) -> str:
        """Get font CSS for body/UI text (Inter)."""
        fam = family or THEME.get("font_family")
        # Don't wrap font family list in quotes - CSS needs: font:700 22px Lato, Inter, sans-serif
        return f"font:{int(weight)} {int(size)}px {fam}"

    @staticmethod
    def heading_font_css(weight: int, size: int, family: str | None = None) -> str:
        """Get font CSS for headings/emphasis (Lato in LIVE/SIM, Inter in DEBUG)."""
        fam = family or THEME.get("heading_font_family")
        # Don't wrap font family list in quotes - CSS needs: font:700 22px Lato, Inter, sans-serif
        return f"font:{int(weight)} {int(size)}px {fam}"

    @staticmethod
    def qfont(weight: int, size_px: int) -> QtGui.QFont:
        """Get QFont for body/UI text (Inter)."""
        f = QtGui.QFont()
        # Split font family string by comma and strip whitespace
        font_families = [fam.strip() for fam in str(THEME.get("font_family")).split(",")]
        f.setFamilies(font_families)
        f.setPixelSize(int(size_px))
        f.setWeight(int(weight))
        return f

    @staticmethod
    def heading_qfont(weight: int, size_px: int) -> QtGui.QFont:
        """Get QFont for headings/emphasis (Lato in LIVE/SIM, Inter in DEBUG)."""
        f = QtGui.QFont()
        # Split font family string by comma and strip whitespace
        font_families = [fam.strip() for fam in str(THEME.get("heading_font_family")).split(",")]
        f.setFamilies(font_families)
        f.setPixelSize(int(size_px))
        f.setWeight(int(weight))
        return f

    # -------------------- PnL Color Logic --------------------
    @staticmethod
    def pnl_color_from_value(value: Optional[float]) -> str:
        from utils.theme_helpers import normalize_color

        if value is None:
            return normalize_color(str(THEME.get("pnl_neu_color", "#C9CDD0")))
        try:
            v = float(value)
        except Exception:
            return normalize_color(str(THEME.get("pnl_neu_color", "#C9CDD0")))
        if v > 0:
            return normalize_color(str(THEME.get("pnl_pos_color", "#20B36F")))
        if v < 0:
            return normalize_color(str(THEME.get("pnl_neg_color", "#C7463D")))
        return normalize_color(str(THEME.get("pnl_neu_color", "#C9CDD0")))

    @staticmethod
    def pnl_color_from_direction(up: Optional[bool]) -> str:
        from utils.theme_helpers import normalize_color

        if up is True:
            return normalize_color(str(THEME.get("pnl_pos_color", "#20B36F")))
        if up is False:
            return normalize_color(str(THEME.get("pnl_neg_color", "#C7463D")))
        return normalize_color(str(THEME.get("pnl_neu_color", "#C9CDD0")))

    @staticmethod
    def pill_color(selected_up: Optional[bool]) -> str:
        return ColorTheme.pnl_color_from_direction(selected_up)

    @staticmethod
    def make_weak_color(color: str, alpha: float = 0.35) -> str:
        """
        Convert any color (hex, oklch) to an rgba string with the specified alpha.
        Example: "#22C55E" with alpha=0.35 -> "rgba(34, 197, 94, 0.35)"

        Args:
            color: Color string (hex, oklch, etc.)
            alpha: Alpha transparency value (0.0 to 1.0)

        Returns:
            RGBA color string (e.g., "rgba(34, 197, 94, 0.35)")
        """
        try:
            from utils.theme_helpers import normalize_color

            # Normalize to hex first
            hex_color = normalize_color(color).lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        except Exception:
            from utils.theme_helpers import normalize_color

            fallback = normalize_color(str(THEME.get("pnl_neu_color", "#C9CDD0")))
            return ColorTheme.make_weak_color(fallback, alpha)


# -------------------------------------------------------------------
# Theme switching functions
# -------------------------------------------------------------------
def switch_theme(theme_name: str) -> None:
    """
    Switch active theme between DEBUG, LIVE, or SIM.

    Args:
        theme_name: One of "debug", "live", or "sim"
    """
    global THEME

    theme_name = theme_name.lower().strip()

    if theme_name == "debug":
        THEME.clear()
        THEME.update(DEBUG_THEME)
    elif theme_name == "live":
        THEME.clear()
        THEME.update(LIVE_THEME)
    elif theme_name == "sim":
        THEME.clear()
        THEME.update(SIM_THEME)
    else:
        # Default to DEBUG if unknown
        THEME.clear()
        THEME.update(DEBUG_THEME)


def apply_trading_mode_theme(mode: str) -> None:
    """
    Apply theme based on trading mode.
    Wrapper for switch_theme() that accepts mode names like DEBUG, LIVE, SIM.

    Args:
        mode: Trading mode - one of "DEBUG", "LIVE", or "SIM"
    """
    switch_theme(mode.lower())


# -------------------------------------------------------------------
# Legacy theme functions (for backward compatibility)
# -------------------------------------------------------------------
def set_theme(mode: str = "dark") -> None:
    """
    Legacy function for backward compatibility.
    Use switch_theme() for new code.
    """
    if mode == "light":
        switch_theme("sim")
    else:
        switch_theme("live")


def set_theme_for_account(account_id: str) -> None:
    """Switch between LIVE and SIM themes based on account ID."""
    if not account_id:
        switch_theme("live")
        return

    acct = account_id.strip().lower()
    if acct == "120005":
        switch_theme("live")
    elif acct == "sim1":
        switch_theme("sim")
    else:
        switch_theme("live")  # default


# -------------------------------------------------------------------
__all__ = [
    "THEME",
    "DEBUG_THEME",
    "LIVE_THEME",
    "SIM_THEME",
    "FONT",
    "ColorTheme",
    "switch_theme",
    "apply_trading_mode_theme",
    "set_theme",
    "set_theme_for_account",
]
# -------------------- config/theme.py (end)
