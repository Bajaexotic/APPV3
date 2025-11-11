import contextlib
import os
import sys

from PyQt6 import QtWidgets

from config.theme import THEME, ColorTheme
from core.app_manager import MainWindow


# Cosmetic UI feature flags (only visible in debug mode)
if os.getenv("DEBUG_DTC", "0") == "1":
    print("ENABLE_GLOW:", THEME.get("ENABLE_GLOW"))
    print("ENABLE_HOVER_ANIMATIONS:", THEME.get("ENABLE_HOVER_ANIMATIONS"))
    print("TOOLTIP_AUTO_HIDE_MS:", THEME.get("TOOLTIP_AUTO_HIDE_MS"))


def main():
    app = QtWidgets.QApplication(sys.argv)
    # Set application font globally from THEME
    with contextlib.suppress(Exception):
        app.setFont(
            ColorTheme.qfont(
                int(THEME.get("ui_font_weight")),
                int(THEME.get("ui_font_size")),
            )
        )
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
