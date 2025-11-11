# widgets/live_pill.py
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME

from .pill_widget import PillWidget


class LivePillWidget(PillWidget):
    """LIVE timeframe pill with grey static dot that pulses when selected."""

    def __init__(self):
        super().__init__()
        self._pulsing = False
        self._dot_visible = True
        self._pulse_phase = 0.0
        self._pulse_timer = QtCore.QTimer(self)
        self._pulse_timer.setInterval(60)  # ~16 FPS
        self._pulse_timer.timeout.connect(self._tick_pulse)

    def set_live_dot_visible(self, visible: bool):
        self._dot_visible = visible
        self.update()

    def set_live_dot_pulsing(self, pulsing: bool):
        self._pulsing = pulsing
        if pulsing:
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        self.update()

    def _tick_pulse(self):
        self._pulse_phase = (self._pulse_phase + 0.07) % 6.283
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._dot_visible:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        size = 8
        if self._pulsing:
            size += 3 * (0.5 + 0.5 * QtCore.qSin(self._pulse_phase))
        r = QtCore.QRect(4, self.height() // 2 - size // 2, size, size)
        painter.setBrush(QtGui.QColor(THEME.get("live_dot_fill", "#22C55E")))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(r)
        painter.end()  # ← FIX: End the painter to prevent QPainter memory leak
