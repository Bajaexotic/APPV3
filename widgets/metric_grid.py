# File: widgets/metric_grid.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict, List, Optional

from PyQt6 import QtWidgets

from config.theme import THEME, ColorTheme
from utils.theme_mixin import ThemeAwareMixin
from widgets.metric_cell import KeyValCard  # type: ignore


class MetricGrid(QtWidgets.QWidget, ThemeAwareMixin):
    """Reusable grid of KeyValCard cells.

    Args:
        metric_names: Flat list of metric display names.
        cols: Number of columns in the grid (rows computed automatically).
        parent: Optional parent widget.

    Public API:
        - update_metric(name, value, color=None) -> None
        - update_many(pairs: Iterable[tuple[str, Any]]) -> None
        - set_enabled_all(enabled: bool) -> None
        - set_enabled(names_or_all: Iterable[str] | str, enabled: bool) -> None
        - metrics() -> Dict[str, KeyValCard]
    """

    def __init__(self, metric_names: list[str], cols: int = 5, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        if not metric_names:
            metric_names = ["-"]
        self._metrics: dict[str, KeyValCard] = {}
        self._cols = max(1, int(cols))
        self._build_grid(metric_names)

    def _build_grid(self, names: Iterable[str]) -> None:
        grid = QtWidgets.QGridLayout(self)
        # Match Panel 2 grid spacing
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for idx, name in enumerate(names):
            label = str(name)
            cell = KeyValCard(label, "--")

            row, col = divmod(idx, self._cols)
            grid.addWidget(cell, row, col)
            self._metrics[label] = cell

    def _infer_color(self, value: Any, color: Optional[str]) -> Optional[str]:
        """Derive green/red/neutral based on numeric sign when color not provided."""
        if color is not None or value is None:
            return color
        try:
            s = str(value).strip().replace("%", "").replace(",", "")
            if s.lower().endswith("x"):
                s = s[:-1]
            v = float(s)
            if v > 0:
                return ColorTheme.pnl_color_from_direction(True)
            if v < 0:
                return ColorTheme.pnl_color_from_direction(False)
            return THEME.get("pnl_neu_color", "#9CA3AF")
        except Exception:
            return color

    # --- Public API ---
    def update_metric(self, name: str, value: Any, color: Optional[str] = None) -> None:
        cell = self._metrics.get(name)
        if not cell:
            return
        text = "--" if value is None else str(value)
        col = self._infer_color(value, color)
        try:
            cell.set_value(text, color=col)  # type: ignore[attr-defined]
        except Exception:
            try:
                if col:
                    cell.setStyleSheet(f"color:{col};")
                if hasattr(cell, "setText"):
                    cell.setText(text)  # type: ignore[attr-defined]
            except Exception:
                pass

        # CRITICAL FIX: Tell Qt to repaint the cell after update
        if hasattr(cell, "update"):
            cell.update()
        if hasattr(cell, "repaint"):
            cell.repaint()

    def update_many(self, pairs: Iterable[tuple[str, Any]]) -> None:
        for name, val in pairs:
            self.update_metric(name, val)

        # CRITICAL FIX: Repaint the entire grid after bulk update
        self.update()
        self.repaint()

    def set_enabled_all(self, enabled: bool) -> None:
        for cell in self._metrics.values():
            cell.setEnabled(enabled)

    def set_enabled(self, names_or_all: Iterable[str] | str, enabled: bool) -> None:
        if isinstance(names_or_all, str) and names_or_all.lower() == "all":
            self.set_enabled_all(enabled)
            return
        for name in names_or_all:
            cell = self._metrics.get(name)
            if cell:
                cell.setEnabled(enabled)

    def metrics(self) -> dict[str, KeyValCard]:
        return self._metrics

    def _get_theme_children(self) -> list:
        """Delegate theme refresh to all metric cells."""
        return list(self._metrics.values())
