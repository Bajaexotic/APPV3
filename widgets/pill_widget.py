# widgets/pill_widget.py
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME


class PillWidget(QtWidgets.QWidget):
    """Base pill-shaped button container."""

    def __init__(self):
        super().__init__()
        self._active_color = THEME.get("accent", "#60A5FA")  # default active color

    def set_active_color(self, hex_color: str):
        self._active_color = hex_color
        self.update()
