from __future__ import annotations

# File: widgets/sharpe_bar.py
# Sharpe Ratio bar widget
from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME


class SharpeBarWidget(QtWidgets.QWidget):
    """
    Minimal horizontal bar to visualize Sharpe Ratio.
    Call set_value() and optional set_color() to update.
    """

    def __init__(self):
        super().__init__()
        self._val: float = 0.0  # current Sharpe
        self._cap: float = 2.0  # max scale (right edge)
        self._color = QtGui.QColor(THEME.get("pnl_pos_color", "#22C55E"))
        self.setMinimumHeight(14)
        self.setMaximumHeight(14)

    # ---- Public API ----
    def set_value(self, v: float):
        try:
            self._val = float(v)
        except Exception:
            self._val = 0.0
        self.update()

    def set_color(self, hex_color: str):
        self._color = QtGui.QColor(hex_color)
        self.update()

    def set_cap(self, cap: float):
        try:
            self._cap = max(0.1, float(cap))
        except Exception:
            self._cap = 2.0
        self.update()

    # ---- Painting ----
    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        r = self.rect().adjusted(0, 0, -1, -1)
        # Track background - use theme-defined colors for sharpe bar
        track_pen = THEME.get("sharpe_track_pen", "rgba(255,255,255,0.16)")
        track_bg = THEME.get("sharpe_track_bg", "rgba(255,255,255,0.10)")
        p.setPen(QtGui.QPen(QtGui.QColor(track_pen if "rgba" in track_pen else "#FFFFFF")))
        p.setBrush(QtGui.QBrush(QtGui.QColor(track_bg if "rgba" in track_bg else "#FFFFFF")))
        p.drawRoundedRect(r, 7, 7)

        # Filled portion
        v = max(0.0, min(self._cap, self._val))
        if v > 0:
            pct = v / self._cap
            w = int(r.width() * pct)
            fill = QtCore.QRect(r.left(), r.top(), max(4, w), r.height())
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(self._color)
            p.drawRoundedRect(fill, 7, 7)

        p.end()
