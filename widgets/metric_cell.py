# File: widgets/metric_cell.py
"""
Unified MetricCell widget used across all panels.
Two-line metric cell: title (top), value (bottom). With color & flashing support.
"""
from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from config.theme import THEME, ColorTheme
from utils.theme_mixin import ThemeAwareMixin


# Flash interval for heat timer alerts
FLASH_INTERVAL_MS = 500


class MetricCell(QtWidgets.QFrame, ThemeAwareMixin):
    """Two-line metric cell: title (top), value (bottom). With color & flashing support."""

    def __init__(self, title: str, initial_value: str = "--"):
        super().__init__()
        self._title = title
        self._initial_value = initial_value
        self._is_flashing = False
        self._flash_on = False
        self._flash_border_color: Optional[str] = None  # Border color to flash with

        self.setObjectName("MetricCell")
        self._build()
        self._setup_theme()

        # Flash timer
        self._flash_timer = QtCore.QTimer(self)
        self._flash_timer.setInterval(FLASH_INTERVAL_MS)
        self._flash_timer.timeout.connect(self._on_flash_tick)

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)

        self.lbl_title = QtWidgets.QLabel(self._title, self)
        self.lbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(f"color: {THEME.get('text_dim')};")

        self.lbl_val = QtWidgets.QLabel(self._initial_value, self)
        self.lbl_val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Fonts
        self.lbl_title.setFont(ColorTheme.qfont(THEME.get("title_font_weight"), THEME.get("title_font_size")))
        self.lbl_val.setFont(ColorTheme.qfont(600, THEME.get("balance_font_size")))

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_val, 1)

        # Panel styling (uses centralized THEME)
        radius = int(THEME.get("card_radius"))
        card_bg = THEME.get("card_bg")
        cell_border = THEME.get("cell_border")  # Uses cell_border from theme (neon blue in SIM mode)

        # If cell_border is "none", use default 1px solid border, otherwise use the theme value
        if cell_border == "none":
            border_style = f"border: 1px solid {THEME.get('border')};"
        else:
            border_style = f"border: {cell_border};"

        self.setStyleSheet(
            f"""
            QFrame#MetricCell {{
                background: {card_bg};
                {border_style}
                border-radius: {radius}px;
            }}
            """
        )

    def _build_theme_stylesheet(self) -> str:
        """Build MetricCell stylesheet using current THEME."""
        radius = int(THEME.get("card_radius"))
        card_bg = THEME.get("card_bg")
        cell_border = THEME.get("cell_border")

        if cell_border == "none":
            border_style = f"border: 1px solid {THEME.get('border')};"
        else:
            border_style = f"border: {cell_border};"

        return f"""
            QFrame#MetricCell {{
                background: {card_bg};
                {border_style}
                border-radius: {radius}px;
            }}
        """

    def _on_theme_refresh(self) -> None:
        """Update label colors after theme refresh."""
        self.lbl_title.setStyleSheet(f"color: {THEME.get('text_dim')};")

    # Value/text/color API
    def set_value_text(self, text: str):
        """Update the displayed value text."""
        self.lbl_val.setText(text)

    def set_value_html(self, html: str):
        """Update the displayed value with HTML (for rich formatting like colored spans)."""
        self.lbl_val.setText(html)

    def set_value_color(self, color_css: str):
        """Update the value text color."""
        self.lbl_val.setStyleSheet(f"color: {color_css};")

    def set_title_color(self, color_css: str):
        """Update the title text color."""
        self.lbl_title.setStyleSheet(f"color: {color_css};")

    def set_value(self, text: str, color: Optional[str] = None):
        """Update value text and optionally color (backwards compatible with KeyValCard API)."""
        self.set_value_text(text)
        if color:
            self.set_value_color(color)

    def start_flashing(self, border_color: Optional[str] = None):
        """
        Start flashing animation (for alerts/warnings).

        Args:
            border_color: Optional border color to flash along with the text
        """
        if not self._is_flashing:
            self._is_flashing = True
            self._flash_on = True
            self._flash_border_color = border_color
            self._flash_timer.start()

    def stop_flashing(self):
        """Stop flashing animation."""
        if self._is_flashing:
            self._is_flashing = False
            self._flash_timer.stop()
            self._flash_border_color = None
            # Ensure visible at end
            self.lbl_val.setGraphicsEffect(None)
            self.setWindowOpacity(1.0)
            # Restore default border
            self.refresh_theme()

    def _on_flash_tick(self):
        """Toggle opacity and border for flashing effect."""
        self._flash_on = not self._flash_on

        # Flash text opacity
        opacity = 1.0 if self._flash_on else 0.35
        eff = QtWidgets.QGraphicsOpacityEffect(self.lbl_val)
        eff.setOpacity(opacity)
        self.lbl_val.setGraphicsEffect(eff)

        # Flash border if color is set
        if self._flash_border_color:
            radius = int(THEME.get("card_radius"))
            card_bg = THEME.get("card_bg")

            if self._flash_on:
                # Show border with flash color
                border_style = f"border: 2px solid {self._flash_border_color};"
            else:
                # Show default border (dim)
                border_style = f"border: 1px solid {THEME.get('border')};"

            self.setStyleSheet(
                f"""
                QFrame#MetricCell {{
                    background: {card_bg};
                    {border_style}
                    border-radius: {radius}px;
                }}
                """
            )


# Alias for backwards compatibility with existing Panel 3 code
KeyValCard = MetricCell


__all__ = ["MetricCell", "KeyValCard"]
