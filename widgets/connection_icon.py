from __future__ import annotations

from datetime import datetime
import time
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME
from utils.theme_helpers import normalize_color
from utils.theme_mixin import ThemeAwareMixin


# -------------------- Timing Thresholds (start)
# Connection layer (outer ring) - based on heartbeat intervals
HEARTBEAT_INTERVAL = 5.0  # Expected heartbeat every 5 seconds
PENDING_THRESHOLD = 5.0  # 1x heartbeat interval -> yellow
DISCONNECT_THRESHOLD = 10.0  # 2x heartbeat interval -> red

# Data layer (inner core) - based on message flow
DATA_ACTIVE_THRESHOLD = 5.0  # Message every <=5s -> green
DATA_STALE_THRESHOLD = 10.0  # 5-15s with no message -> yellow
DATA_DEAD_THRESHOLD = 15.0  # >15s with no message -> red
# -------------------- Timing Thresholds (end)


# -------------------- Visual Constants (start)
OUTER_RING_WIDTH = 3  # Outer ring stroke width
INNER_CORE_INSET = 5  # Inner core inset from outer edge
# -------------------- Visual Constants (end)


class ConnectionIcon(QtWidgets.QWidget, ThemeAwareMixin):
    """
    Dual-circle connection status indicator with stoplight logic.

    Structure:
    - Outer ring -> Connection health (DTC link, heartbeats)
    - Inner core -> Data feed vitality (live trade/balance updates)

    Colors (OKLCH-based, perceptually balanced):
    - Green: Healthy/Normal
    - Yellow: Transitional/Caution
    - Red: Failure/Critical
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 11099) -> None:
        super().__init__()
        self._host = host
        self._port = port

        # Timing state
        self._last_heartbeat_time: Optional[float] = None  # Epoch timestamp
        self._last_data_time: Optional[float] = None  # Epoch timestamp

        # Color state (computed from timing)
        self._outer_color: str = "red"  # Start red (disconnected)
        self._inner_color: str = "red"  # Start red (no data)

        # Update timer (checks thresholds every second)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._update_colors)
        self._timer.start(1000)  # 1 second interval

        self.setFixedSize(18, 18)
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._update_tooltip()

    # ---- Public API -----------------------------------------------------
    def mark_heartbeat(self) -> None:
        """Called when a heartbeat is received from DTC (updates outer ring)."""
        self._last_heartbeat_time = time.time()
        self._update_colors()
        self._update_tooltip()

    def mark_data_activity(self) -> None:
        """Called when a data message is received (updates inner core)."""
        self._last_data_time = time.time()
        self._update_colors()
        self._update_tooltip()

    def mark_connected(self) -> None:
        """Called when DTC connection is established (starts heartbeat timer)."""
        self.mark_heartbeat()

    def mark_disconnected(self) -> None:
        """Called when DTC connection is lost (clears all timers)."""
        self._last_heartbeat_time = None
        self._last_data_time = None
        self._update_colors()
        self._update_tooltip()

    def _on_theme_refresh(self) -> None:
        """Custom refresh logic: update colors and tooltip."""
        self._update_colors()
        self._update_tooltip()

    # ---- Internal: Color Logic ------------------------------------------
    def _update_colors(self) -> None:
        """Compute outer and inner colors based on timing thresholds."""
        now = time.time()

        # Outer ring (connection health)
        if self._last_heartbeat_time is None:
            self._outer_color = "red"  # Never connected
        else:
            elapsed = now - self._last_heartbeat_time
            if elapsed <= PENDING_THRESHOLD:
                self._outer_color = "green"  # Healthy
            elif elapsed <= DISCONNECT_THRESHOLD:
                self._outer_color = "yellow"  # Reconnecting
            else:
                self._outer_color = "red"  # Disconnected

        # Inner core (data feed vitality)
        if self._last_data_time is None:
            self._inner_color = "red"  # No data yet
        else:
            elapsed = now - self._last_data_time
            if elapsed <= DATA_ACTIVE_THRESHOLD:
                self._inner_color = "green"  # Active data flow
            elif elapsed <= DATA_DEAD_THRESHOLD:
                self._inner_color = "yellow"  # Data delay/lull
            else:
                self._inner_color = "red"  # Feed frozen

        self.update()

    def _get_color_hex(self, state: str) -> str:
        """Get hex color from THEME based on stoplight state."""
        color_map = {
            "green": THEME.get("conn_status_green"),
            "yellow": THEME.get("conn_status_yellow"),
            "red": THEME.get("conn_status_red"),
        }
        return normalize_color(color_map.get(state, "#808080"))

    # ---- Internal: Tooltip ----------------------------------------------
    def _update_tooltip(self) -> None:
        """Update tooltip with connection status details."""
        # Outer ring status
        if self._outer_color == "green":
            outer_status = "Connected (heartbeats active)"
        elif self._outer_color == "yellow":
            outer_status = "Reconnecting (heartbeat delayed)"
        else:
            outer_status = "Disconnected (no heartbeat)"

        # Inner core status
        if self._inner_color == "green":
            inner_status = "Receiving live data"
        elif self._inner_color == "yellow":
            inner_status = "Data delayed"
        else:
            inner_status = "No data feed"

        # Last update times
        hb_time = (
            datetime.fromtimestamp(self._last_heartbeat_time).strftime("%H:%M:%S")
            if self._last_heartbeat_time
            else "Never"
        )
        data_time = (
            datetime.fromtimestamp(self._last_data_time).strftime("%H:%M:%S") if self._last_data_time else "Never"
        )

        # Build tooltip
        bg_color = normalize_color(THEME["bg_panel"])
        text_color = normalize_color(THEME["ink"])
        font_family = THEME["font_family"]
        font_size = int(THEME["font_size"])
        font_weight = int(THEME["font_weight"])
        border_color = normalize_color(THEME["border"])

        outer_hex = self._get_color_hex(self._outer_color)
        inner_hex = self._get_color_hex(self._inner_color)

        html = (
            f"<div style='background:{bg_color}; color:{text_color}; "
            f"font-family:{font_family}; font-size:{font_size}px; font-weight:{font_weight}; "
            f"border:1px solid {border_color}; padding:5px 7px; border-radius:4px;'>"
            f"<b>Sierra Connection</b><br>"
            f"Outer (Connection): <b style='color:{outer_hex};'>{outer_status}</b><br>"
            f"Inner (Data Feed): <b style='color:{inner_hex};'>{inner_status}</b><br>"
            f"Host: {self._host}  Port: {self._port}<br>"
            f"Last Heartbeat: {hb_time}<br>"
            f"Last Data: {data_time}</div>"
        )
        self.setToolTip(html)

    # ---- Qt Overrides ---------------------------------------------------
    def closeEvent(self, ev: QtGui.QCloseEvent) -> None:
        """Stop timer on close."""
        try:
            if self._timer and self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass
        super().closeEvent(ev)

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        """Paint dual-circle indicator."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Get colors from THEME
        outer_hex = self._get_color_hex(self._outer_color)
        inner_hex = self._get_color_hex(self._inner_color)

        # Outer ring (connection health)
        outer_color = QtGui.QColor(outer_hex)
        pen = QtGui.QPen(outer_color, OUTER_RING_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # Draw outer ring circle
        ring_rect = QtCore.QRectF(
            OUTER_RING_WIDTH / 2,
            OUTER_RING_WIDTH / 2,
            self.width() - OUTER_RING_WIDTH,
            self.height() - OUTER_RING_WIDTH,
        )
        painter.drawEllipse(ring_rect)

        # Inner core (data feed)
        inner_color = QtGui.QColor(inner_hex)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(inner_color)

        # Draw inner core circle
        core_rect = QtCore.QRectF(
            INNER_CORE_INSET,
            INNER_CORE_INSET,
            self.width() - 2 * INNER_CORE_INSET,
            self.height() - 2 * INNER_CORE_INSET,
        )
        painter.drawEllipse(core_rect)
