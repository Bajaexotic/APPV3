# -------------------- widgets/timeframe_pills.py (start)
# File: widgets/timeframe_pills.py
from __future__ import annotations

from typing import Dict, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME, ColorTheme
from utils.theme_helpers import normalize_color


# ------------------------------
# Shared style helpers
# ------------------------------
def _pill_qss_base() -> str:
    radius = int(THEME.get("pill_radius"))
    height = int(THEME.get("chip_height"))
    font_css = ColorTheme.font_css(
        int(THEME.get("pill_font_weight")),
        int(THEME.get("pill_font_size")),
    )
    ink_muted = THEME.get("fg_muted")
    bg = THEME.get("bg_secondary")
    bg_active = THEME.get("accent")
    text_active = THEME.get("pill_text_active_color")
    border_color = THEME.get("border")
    # Note: we keep background transparent for normal state; active shows accent
    return (
        "QToolButton {"
        f"  color:{ink_muted};"
        f"  background:transparent;"
        f"  border:1px solid {border_color};"
        f"  border-radius:{radius}px;"
        f"  padding:0 14px;"
        f"  height:{height}px;"
        f"  {font_css};"
        "}"
        "QToolButton:checked {"
        f"  color:{text_active};"
        f"  background:{bg_active};"
        f"  border:1px solid {border_color};"
        "}"
        "QToolButton:hover {"
        f"  background:{bg};"
        "}"
    )


def _apply_active_color(button: QtWidgets.QToolButton, hex_color: str) -> None:
    """
    Override only the active (:checked) background color while preserving the base QSS.
    Use an additive override rule to avoid brittle string surgery and malformed QSS.
    """
    base = _pill_qss_base()
    text_active = THEME.get("pill_text_active_color")
    override = f"QToolButton:checked {{ color:{text_active}; background:{hex_color}; }}"
    button.setStyleSheet(base + override)


# ------------------------------
# LivePillButton — LIVE pill with an internal pulsing dot
# ------------------------------
class LivePillButton(QtWidgets.QToolButton):
    """
    A QToolButton that renders a small dot INSIDE the pill (left side),
    and can pulse via opacity changes. The dot is a child widget, so it
    sits within the pill’s rounded background.
    """

    def __init__(self, text: str = "LIVE", parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setStyleSheet(_pill_qss_base())

        # Child dot inside the button
        self._dot = QtWidgets.QFrame(self)
        self._dot.setObjectName("LiveDot")
        self._dot.setFixedSize(10, 10)  # diameter
        fill = THEME.get("live_dot_fill")  # Green dot fill (matches OKLCH positive PnL)
        border = THEME.get("live_dot_border")  # Darker green border
        self._dot.setStyleSheet(
            f"""
            QFrame#LiveDot {{
                background: {fill};
                border: 1px solid {border};
                border-radius: 5px;
            }}
            """
        )

        # Opacity effect for pulsing
        self._eff = QtWidgets.QGraphicsOpacityEffect(self._dot)
        self._dot.setGraphicsEffect(self._eff)
        self._eff.setOpacity(1.0)

        # Timer for pulse
        self._pulsing = False
        self._pulse_on = True
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(int(THEME["live_dot_pulse_ms"]))
        self._timer.timeout.connect(self._on_pulse_tick)

        # Keep some extra left padding so text doesn’t collide with the dot
        # (We already have padding in QSS; we just position the dot precisely.)
        self._left_inset_px = 10  # distance from left edge to dot center + radius margin

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:  # type: ignore[name-defined]
        super().resizeEvent(ev)
        self._reposition_dot()

    def _reposition_dot(self) -> None:
        # Place the dot near the left, vertically centered
        h = self.height()
        d = self._dot.height()
        y = (h - d) // 2
        x = 5  # slight inset from left edge, within pill padding
        self._dot.move(x, y)

    # External API
    def set_live_dot_visible(self, visible: bool) -> None:
        self._dot.setVisible(bool(visible))

    def set_live_dot_pulsing(self, pulsing: bool) -> None:
        pulsing = bool(pulsing)
        if pulsing == self._pulsing:
            return
        self._pulsing = pulsing
        if self._pulsing:
            self._pulse_on = True
            self._eff.setOpacity(1.0)
            self._timer.start()
        else:
            self._timer.stop()
            self._eff.setOpacity(1.0)

    def _on_pulse_tick(self) -> None:
        self._pulse_on = not self._pulse_on
        self._eff.setOpacity(1.0 if self._pulse_on else 0.35)


# ------------------------------
# InvestingTimeframePills — used by Panel 2
# ------------------------------
class InvestingTimeframePills(QtWidgets.QWidget):
    """
    Timeframe pills with a LIVE pill that contains a pulsing dot INSIDE the button.
    API used by panels:
      - timeframeChanged(str)
      - set_active_color(hex_color: str)
      - set_live_dot_visible(visible: bool)
      - set_live_dot_pulsing(pulsing: bool)
    """

    timeframeChanged = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._timeframes = ["LIVE", "1D", "1W", "1M", "3M", "YTD"]
        self._pills: dict[str, QtWidgets.QToolButton] = {}
        self._live_btn: Optional[LivePillButton] = None
        self._current_tf = "LIVE"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(int(THEME["gap_md"]))
        layout.setContentsMargins(0, 0, 0, 0)

        base_qss = _pill_qss_base()

        for tf in self._timeframes:
            if tf == "LIVE":
                btn = LivePillButton("LIVE")
                self._live_btn = btn
            else:
                btn = QtWidgets.QToolButton()
                btn.setText(tf)
                btn.setCheckable(True)
                btn.setStyleSheet(base_qss)

            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
            btn.clicked.connect(lambda checked, t=tf: self._on_pill_clicked(t))
            layout.addWidget(btn)
            self._pills[tf] = btn

        # Default selection
        self._pills["LIVE"].setChecked(True)
        if self._live_btn:
            self._live_btn.set_live_dot_visible(True)
            self._live_btn.set_live_dot_pulsing(True)

    # -------- Interaction
    def _on_pill_clicked(self, tf_name: str) -> None:
        self.set_timeframe(tf_name)

    def set_timeframe(self, tf_name: str) -> None:
        if tf_name not in self._pills:
            return
        self._current_tf = tf_name
        for tf, pill in self._pills.items():
            pill.setChecked(tf == tf_name)
        if self._live_btn:
            self._live_btn.set_live_dot_pulsing(tf_name == "LIVE")
        self.timeframeChanged.emit(tf_name)

    # -------- Theming hooks used by panels
    def set_active_color(self, hex_color: str) -> None:
        """Safely recolor the active (:checked) pill background.
        Caches last color to avoid unnecessary QSS resets.
        """
        try:
            if not isinstance(hex_color, str) or not hex_color:
                return
            if getattr(self, "_last_active_hex", None) == hex_color:
                return
            self._last_active_hex = hex_color
            for pill in self._pills.values():
                _apply_active_color(pill, hex_color)
        except Exception:
            pass

    def set_live_dot_visible(self, visible: bool) -> None:
        if self._live_btn:
            self._live_btn.set_live_dot_visible(visible)

    def set_live_dot_pulsing(self, pulsing: bool) -> None:
        if self._live_btn:
            self._live_btn.set_live_dot_pulsing(pulsing)

    def refresh_theme(self) -> None:
        """Refresh all pills with current THEME colors."""
        base_qss = _pill_qss_base()
        for tf, pill in self._pills.items():
            pill.setStyleSheet(base_qss)
        # Re-apply active color if we have one cached
        if hasattr(self, "_last_active_hex") and self._last_active_hex:
            for pill in self._pills.values():
                _apply_active_color(pill, self._last_active_hex)


# ------------------------------
# TradingStatsTimeframePills — Panel 3
# ------------------------------
class TradingStatsTimeframePills(QtWidgets.QWidget):
    """Timeframe pills for the Trading Stats panel (Panel 3)."""

    timeframeChanged = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._timeframes = ["1D", "1W", "1M", "3M", "YTD"]
        self._pills: dict[str, QtWidgets.QToolButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(int(THEME["gap_md"]))
        layout.setContentsMargins(0, 0, 0, 0)

        base_qss = _pill_qss_base()

        for tf in self._timeframes:
            pill = QtWidgets.QToolButton()
            pill.setText(tf)
            pill.setCheckable(True)
            pill.setStyleSheet(base_qss)
            pill.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
            pill.clicked.connect(lambda checked, t=tf: self._on_pill_clicked(t))
            layout.addWidget(pill)
            self._pills[tf] = pill

        # default
        self._pills["1D"].setChecked(True)

    def _on_pill_clicked(self, tf_name: str) -> None:
        for tf, pill in self._pills.items():
            pill.setChecked(tf == tf_name)
        self.timeframeChanged.emit(tf_name)

    # Match Panel 2 behavior: allow active color override
    def set_active_color(self, hex_color: str) -> None:
        try:
            if not isinstance(hex_color, str) or not hex_color:
                return
            if getattr(self, "_last_active_hex", None) == hex_color:
                return
            self._last_active_hex = hex_color
            for pill in self._pills.values():
                _apply_active_color(pill, hex_color)
        except Exception:
            pass

    def refresh_theme(self) -> None:
        """Refresh all pills with current THEME colors."""
        base_qss = _pill_qss_base()
        for tf, pill in self._pills.items():
            pill.setStyleSheet(base_qss)
        # Re-apply active color if we have one cached
        if hasattr(self, "_last_active_hex") and self._last_active_hex:
            for pill in self._pills.values():
                _apply_active_color(pill, self._last_active_hex)


__all__ = ["InvestingTimeframePills", "TradingStatsTimeframePills", "LivePillButton"]
# -------------------- widgets/timeframe_pills.py (end)
