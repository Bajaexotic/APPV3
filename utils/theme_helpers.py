from __future__ import annotations

# File: utils/theme_helpers.py
# Unified styling and theme helpers for SierraPnL app
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from config.theme import THEME


# -------------------- base styling (start)
def apply_theme(widget: QtWidgets.QWidget, bg: str | None = None, fg: str | None = None) -> None:
    """
    Apply background/foreground colors to a widget using THEME tokens.
    """
    if widget is None:
        return
    bgc = normalize_color(bg or THEME.get("bg_primary", "#000000"))
    fgc = normalize_color(fg or THEME.get("ink", "#E5E7EB"))
    widget.setStyleSheet(f"background:{bgc}; color:{fgc};")


# -------------------- base styling (end)


# -------------------- card styling (start)
def style_card(widget: QtWidgets.QWidget) -> None:
    """Apply card-like rounded style to a widget."""
    if widget is None:
        return
    card_bg = normalize_color(THEME.get("card_bg", "#1A1F2E"))
    card_radius = int(THEME.get("card_radius", 8))
    border = normalize_color(THEME.get("border", "#374151"))
    ink = normalize_color(THEME.get("ink", "#E5E7EB"))
    widget.setStyleSheet(
        f"background:{card_bg}; border-radius:{card_radius}px; " f"border:1px solid {border}; color:{ink};"
    )


# -------------------- card styling (end)


# -------------------- global refresh (start)
def refresh_theme_all(app: QtWidgets.QApplication) -> None:
    """Iterate over all top-level widgets and reapply base theme."""
    if app is None:
        return
    for w in app.topLevelWidgets():
        apply_theme(w)


# -------------------- global refresh (end)


# -------------------- repolish (start)
def repolish_all(app: QtWidgets.QApplication) -> None:
    """Force Qt to unpolish/polish widgets so new stylesheets take effect immediately."""
    if app is None:
        return
    try:
        style = app.style()
        for w in app.allWidgets():
            try:
                style.unpolish(w)
                style.polish(w)
                w.update()
            except Exception:
                continue
    except Exception:
        pass


# -------------------- repolish (end)


# -------------------- badge & connection indicators (start)
def apply_badge_style(mode: str, badge: Optional[QtWidgets.QLabel]) -> None:
    """
    Updates the existing LIVE/SIM badge styling based on theme mode.
    Mode: 'dark' => LIVE, 'light' => SIM
    """
    if not badge:
        return
    if mode == "dark":
        text, bg, fg = (
            "LIVE",
            normalize_color(THEME["badge_live_bg"]),
            normalize_color(THEME["badge_live_fg"]),
        )
        tooltip = "Connected to LIVE account (120005)"
    else:
        text, bg, fg = (
            "SIM",
            normalize_color(THEME["badge_sim_bg"]),
            normalize_color(THEME["badge_sim_fg"]),
        )
        tooltip = "Simulation Mode (Sim1)"
    badge.setText(text)
    badge.setToolTip(tooltip)
    border_color = hex_to_rgba(THEME["border"], 0.15)
    badge.setStyleSheet(
        f"color:{fg}; background:{bg}; border-radius:{THEME['badge_border_radius']}px; "
        f"border:1px solid {border_color}; padding:4px 10px; "
        f"font:{THEME['badge_font_weight']} {THEME['badge_font_size']}px {THEME['font_family']};"
    )


# -------------------- badge & connection indicators (end)


# -------------------- panel styling (start)
def apply_panel_style(panel: QtWidgets.QWidget, role: str) -> None:
    """
    Apply themed panel background colors based on panel role.
    Roles: 'balance', 'live', 'stats'
    """
    if panel is None:
        return
    colors = {
        "balance": normalize_color(THEME.get("bg_panel", "#0B0F14")),
        "live": normalize_color(THEME.get("bg_secondary", "#1E293B")),
        "stats": normalize_color(THEME.get("bg_primary", "#111827")),
    }
    bg = colors.get(role, normalize_color(THEME.get("bg_primary", "#111827")))
    ink = normalize_color(THEME.get("ink", "#E5E7EB"))
    panel.setStyleSheet(f"background:{bg}; color:{ink}; border:0;")


# -------------------- panel styling (end)


# -------------------- pnl helpers (start)
def pnl_color(value: Optional[float]) -> str:
    """Return green/red/neutral color for numeric PnL values."""
    if value is None:
        return normalize_color(THEME.get("pnl_neu_color", "#9CA3AF"))
    try:
        val = float(value)
    except Exception:
        return normalize_color(THEME.get("pnl_neu_color", "#9CA3AF"))
    if val > 0:
        return normalize_color(THEME.get("pnl_pos_color", "#22C55E"))
    if val < 0:
        return normalize_color(THEME.get("pnl_neg_color", "#EF4444"))
    return normalize_color(THEME.get("pnl_neu_color", "#9CA3AF"))


# -------------------- pnl helpers (end)


# -------------------- color utils (start)
def hex_to_rgba(color: str, opacity: float = 1.0) -> str:
    """
    Convert any color (hex, oklch, rgb) to an RGBA string usable in QSS.
    Example: "#2563EB", 0.3 -> "rgba(37,99,235,0.3)"
    Example: "oklch(0.7 0.15 140)", 0.5 -> "rgba(123,200,50,0.5)"
    """
    # Handle OKLCH format
    if color.startswith("oklch("):
        r, g, b = oklch_to_rgb(color)
        return f"rgba({r},{g},{b},{opacity})"

    # Handle hex format
    hc = color.lstrip("#")
    if len(hc) != 6:
        # Fallback to theme ink color instead of hardcoded white
        fallback = normalize_color(THEME.get("ink", "#FFFFFF"))
        fallback = fallback.lstrip("#")
        r, g, b = (int(fallback[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{opacity})"
    r, g, b = (int(hc[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{opacity})"


def blend_colors(hex1: str, hex2: str, alpha: float) -> str:
    """
    Blend two hex colors by alpha (0.0–1.0) and return a new hex color.
    """

    def _h2r(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    c1, c2 = _h2r(hex1), _h2r(hex2)
    blended = tuple(int((1 - alpha) * c1[i] + alpha * c2[i]) for i in range(3))
    return "#%02x%02x%02x" % blended


def oklch_to_rgb(oklch_str: str) -> tuple[int, int, int]:
    """
    Convert OKLCH color string to RGB tuple.
    Example: "oklch(0.7 0.15 140)" -> (123, 200, 50)
    """
    import math
    import re

    # Parse OKLCH string
    match = re.match(r"oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+([\d.]+)\s*\)", oklch_str.strip())
    if not match:
        return (255, 255, 255)  # Fallback white

    L = float(match.group(1))
    C = float(match.group(2))
    H = float(match.group(3))

    # Convert percentage to 0-1 range if needed
    if "%" in oklch_str:
        L = L / 100.0

    # OKLCH to OKLab
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))

    # OKLab to linear RGB
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_

    r_lin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g_lin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_lin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    # Linear RGB to sRGB with gamma correction
    def linear_to_srgb(c: float) -> int:
        val = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055
        return max(0, min(255, int(round(val * 255))))

    return (linear_to_srgb(r_lin), linear_to_srgb(g_lin), linear_to_srgb(b_lin))


def oklch_to_hex(oklch_str: str) -> str:
    """
    Convert OKLCH color string to hex.
    Example: "oklch(0.7 0.15 140)" -> "#7bc832"
    """
    r, g, b = oklch_to_rgb(oklch_str)
    return f"#{r:02x}{g:02x}{b:02x}"


def normalize_color(color: str) -> str:
    """
    Takes any color format (oklch, hex, rgb, rgba) and returns hex.
    This is the main function to use when getting colors from THEME.
    """
    if not color or color == "none":
        return "#000000"

    color = color.strip()

    # Handle OKLCH format
    if color.startswith("oklch("):
        return oklch_to_hex(color)

    # Handle hex format
    if color.startswith("#"):
        return color

    # Handle rgba format - extract RGB part
    if color.startswith("rgba("):
        import re

        match = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)", color)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return f"#{r:02x}{g:02x}{b:02x}"

    # Handle rgb format
    if color.startswith("rgb("):
        import re

        match = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return f"#{r:02x}{g:02x}{b:02x}"

    # Fallback
    return "#000000"


# -------------------- color utils (end)


# -------------------- plot & graph theming (start)
def apply_plot_theme(plot_widget, mode: str) -> None:
    """
    Adjust PyQtGraph plot visuals based on the theme mode (dark/light).
    """
    if plot_widget is None:
        return
    try:
        import pyqtgraph as pg  # available per user's environment (0.13.7)

        if mode == "dark":
            bg = normalize_color(THEME.get("bg_panel", "#0B0F14"))
            fg = normalize_color(THEME.get("fg_primary", "#E5E7EB"))
            grid_color = THEME.get("grid_color", "#464646")  # Default dark grid
            grid_rgb = tuple(int(grid_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
            alpha = 0.25
        else:
            bg = normalize_color(THEME.get("bg_panel", "#FFFFFF"))
            fg = normalize_color(THEME.get("fg_primary", "#111827"))
            grid_color = THEME.get("grid_color", "#D2D2D2")  # Default light grid
            grid_rgb = tuple(int(grid_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
            alpha = 0.5

        plot_widget.setBackground(bg)
        # Axis pens
        plot_widget.getAxis("left").setTextPen(pg.mkPen(fg))
        plot_widget.getAxis("bottom").setTextPen(pg.mkPen(fg))
        # Grid
        plot_widget.showGrid(x=True, y=True, alpha=alpha, pen=pg.mkPen(grid_rgb))
    except Exception:
        # Silently ignore styling if pyqtgraph not ready
        pass


def get_pnl_pen(mode: str, pnl_state: str = "neutral", width: float = 2.0):
    """
    Return a pyqtgraph pen based on PnL polarity and current theme.
    pnl_state: 'positive', 'negative', or 'neutral'
    """
    import pyqtgraph as pg

    color_map = {
        "positive": normalize_color(THEME.get("pnl_pos_color", "#22C55E")),
        "negative": normalize_color(THEME.get("pnl_neg_color", "#EF4444")),
        "neutral": normalize_color(THEME.get("pnl_neu_color", "#9CA3AF")),
    }
    color = color_map.get(str(pnl_state).lower(), color_map["neutral"])
    pen_width = width if mode == "dark" else max(1.0, width * 0.9)
    return pg.mkPen(color, width=pen_width)


# -------------------- plot & graph theming (end)


# -------------------- animated transitions (start)
def animate_pnl_color(plot_line, start_hex: str, end_hex: str, duration_ms: int = 350, steps: int = 20) -> None:
    """
    Smoothly transition the color of a pyqtgraph line from start_hex to end_hex.
    Uses blend_colors() for interpolation.
    """
    if plot_line is None:
        return
    try:
        import pyqtgraph as pg
    except Exception:
        return

    # local counter to avoid free-variable rebind issues
    counter = {"i": 0}
    step_interval = max(1, duration_ms // max(1, steps))

    timer = QtCore.QTimer()
    timer.setInterval(step_interval)

    def update_color():
        alpha = counter["i"] / float(steps)
        blended = blend_colors(start_hex, end_hex, alpha)
        pen = pg.mkPen(blended, width=2)
        plot_line.setPen(pen)
        counter["i"] += 1
        if counter["i"] > steps:
            timer.stop()

    timer.timeout.connect(update_color)
    timer.start()


# -------------------- animated transitions (end)

__all__ = [
    "apply_theme",
    "style_card",
    "refresh_theme_all",
    "repolish_all",
    "apply_badge_style",
    "apply_panel_style",
    "pnl_color",
    "hex_to_rgba",
    "blend_colors",
    "oklch_to_rgb",
    "oklch_to_hex",
    "normalize_color",
    "apply_plot_theme",
    "get_pnl_pen",
    "animate_pnl_color",
]
