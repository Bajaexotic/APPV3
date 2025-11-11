# File: utils/ui_helpers.py
from __future__ import annotations

from typing import Optional, Tuple

from PyQt6 import QtWidgets


def centered_row(widget: QtWidgets.QWidget, left_stretch: int = 1, right_stretch: int = 1) -> QtWidgets.QHBoxLayout:
    """Return an HBox layout that centers the given widget with symmetric stretches.

    Args:
        widget: The widget to center horizontally.
        left_stretch: Stretch factor on the left side (default 1).
        right_stretch: Stretch factor on the right side (default 1).
    """
    row = QtWidgets.QHBoxLayout()
    row.addStretch(left_stretch)
    row.addWidget(widget)
    row.addStretch(right_stretch)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    return row


def centered_title(
    text: str, parent: Optional[QtWidgets.QWidget] = None, object_name: str = "panelTitle"
) -> tuple[QtWidgets.QLabel, QtWidgets.QHBoxLayout]:
    """Create a QLabel for a title and return it with a centered row layout.

    Returns:
        (label, layout): The created label and an HBox layout that centers it.
    """
    label = QtWidgets.QLabel(text, parent)
    label.setObjectName(object_name)
    row = centered_row(label)
    return label, row


__all__ = ["centered_row", "centered_title"]
