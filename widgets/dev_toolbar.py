from __future__ import annotations

import contextlib

# File: widgets/dev_toolbar.py
# Block 11/?? Ã¢â‚¬â€ DevToolbar (stub + interface)
from PyQt6 import QtCore, QtWidgets

from config.theme import THEME


class DevToolbar(QtWidgets.QWidget):
    """Small toolbar with Theme toggle and font size controls.
    Emits `changed` so MainWindow can refresh styles.
    """

    changed = QtCore.pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        self.btn_theme = QtWidgets.QPushButton("Theme")
        self.btn_theme.setFixedHeight(28)
        self.btn_theme.clicked.connect(self._toggle_theme)

        self.btn_font_up = QtWidgets.QPushButton("A+")
        self.btn_font_up.setFixedHeight(28)
        self.btn_font_up.clicked.connect(self._font_up)

        self.btn_font_down = QtWidgets.QPushButton("A-")
        self.btn_font_down.setFixedHeight(28)
        self.btn_font_down.clicked.connect(self._font_down)

        layout.addWidget(self.btn_theme)
        layout.addWidget(self.btn_font_up)
        layout.addWidget(self.btn_font_down)
        layout.addStretch(1)

        self.setStyleSheet("background: transparent;")

    # ---- Slots ----
    def _toggle_theme(self):
        """Cycle through DEBUG -> SIM -> LIVE -> DEBUG themes"""
        current = getattr(self.main_window, "current_theme_mode", "LIVE")
        theme_cycle = {"DEBUG": "SIM", "SIM": "LIVE", "LIVE": "DEBUG"}
        new = theme_cycle.get(current, "LIVE")

        with contextlib.suppress(Exception):
            # Call the theme mode setter if available
            if hasattr(self.main_window, "_set_theme_mode"):
                self.main_window._set_theme_mode(new)
            elif hasattr(self.main_window, "apply_theme"):
                self.main_window.apply_theme(new)
        self.changed.emit()

    def _font_up(self):
        try:
            THEME["font_base_size"] = int(THEME.get("font_base_size", 13) + 1)
        except Exception:
            THEME["font_base_size"] = 14
        self.changed.emit()

    def _font_down(self):
        try:
            THEME["font_base_size"] = max(10, int(THEME.get("font_base_size", 13) - 1))
        except Exception:
            THEME["font_base_size"] = 12
        self.changed.emit()
