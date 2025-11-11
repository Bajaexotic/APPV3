"""
Temporary Mode Selector for Trading Mode (DEBUG/LIVE/SIM)

Simple hotkey-based mode cycling: Ctrl+Shift+M

TO REMOVE: Once DTC auto-detection is working, delete this file and remove imports.

Usage:
    # In MainWindow.__init__
    from utils.mode_selector import setup_mode_hotkey
    setup_mode_hotkey(self)

    # Then use Ctrl+Shift+M to cycle: DEBUG → SIM → LIVE → DEBUG
"""

from PyQt6.QtGui import QKeySequence, QShortcut

from config import settings
from core.diagnostics import info


def setup_mode_hotkey(window):
    """
    Setup Ctrl+Shift+M hotkey to cycle through trading modes.

    Cycles: DEBUG → SIM → LIVE → DEBUG

    Updates:
    - Panel 1 badge (DEBUG/SIM/LIVE text and neon glow)
    - Application theme (grey/white/black backgrounds)
    - Terminal output behavior (only DEBUG shows console output)

    Args:
        window: Main window instance (should have panel_balance attribute)

    Example:
        class MainWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                from utils.mode_selector import setup_mode_hotkey
                setup_mode_hotkey(self)  # ← Add this line

    TO REMOVE: Delete this call once DTC auto-detection works.
    """
    MODE_ORDER = ["DEBUG", "SIM", "LIVE"]

    def cycle_mode():
        """Cycle through modes and update badge + theme"""
        try:
            current_index = MODE_ORDER.index(settings.TRADING_MODE)
        except ValueError:
            current_index = 0

        next_index = (current_index + 1) % len(MODE_ORDER)
        new_mode = MODE_ORDER[next_index]
        previous_mode = settings.TRADING_MODE

        # Update settings
        settings.TRADING_MODE = new_mode

        # Log the change
        info(
            "ui",
            f"Trading mode switched: {previous_mode} → {new_mode}",
            context={
                "new_mode": new_mode,
                "previous_mode": previous_mode,
                "method": "hotkey",
                "hotkey": "Ctrl+Shift+M",
            },
        )

        # Update Panel 1 badge
        try:
            if hasattr(window, "panel_balance"):
                panel1 = window.panel_balance
                if hasattr(panel1, "set_trading_mode"):
                    panel1.set_trading_mode(new_mode)
                    info("ui", f"Panel 1 badge updated: {new_mode}")
        except Exception as e:
            print(f"[MODE] Warning: Could not update panel badge: {e}")

        # Apply trading mode theme
        try:
            from config.theme import apply_trading_mode_theme

            apply_trading_mode_theme(new_mode)
            info("ui", f"Theme applied: {new_mode}")
        except Exception as e:
            print(f"[MODE] Warning: Could not apply theme: {e}")

        # Refresh timeframe pill colors in Panel 2 and Panel 3
        try:
            if hasattr(window, "panel_live"):
                panel2 = window.panel_live
                if hasattr(panel2, "refresh_pill_colors"):
                    panel2.refresh_pill_colors()
                    info("ui", "Panel 2 pill colors refreshed")
        except Exception as e:
            print(f"[MODE] Warning: Could not refresh Panel 2 pills: {e}")

        try:
            if hasattr(window, "panel_trading"):
                panel3 = window.panel_trading
                if hasattr(panel3, "refresh_pill_colors"):
                    panel3.refresh_pill_colors()
                    info("ui", "Panel 3 pill colors refreshed")
        except Exception as e:
            print(f"[MODE] Warning: Could not refresh Panel 3 pills: {e}")

        # Force UI refresh
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                # Refresh all widgets
                for widget in app.allWidgets():
                    widget.update()
                window.update()
        except Exception as e:
            print(f"[MODE] Warning: Could not refresh UI: {e}")

        # Show notification in status bar
        if hasattr(window, "statusBar"):
            mode_descriptions = {
                "DEBUG": "Development Mode (Grey/Silver)",
                "SIM": "Simulation Mode (White/Neon Blue)",
                "LIVE": "Live Trading Mode (Black/Gold)",
            }
            window.statusBar().showMessage(
                f"{mode_descriptions.get(new_mode, new_mode)} | Ctrl+Shift+M to cycle",
                5000,  # 5 seconds
            )

        print(f"[MODE] Switched to: {new_mode}")

    # Create the shortcut
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), window)
    shortcut.activated.connect(cycle_mode)

    info(
        "system",
        "Mode cycling hotkey enabled: Ctrl+Shift+M",
        context={"hotkey": "Ctrl+Shift+M", "modes": MODE_ORDER, "current_mode": settings.TRADING_MODE},
    )

    # Initial notification
    if hasattr(window, "statusBar"):
        window.statusBar().showMessage(f"Mode: {settings.TRADING_MODE} | Press Ctrl+Shift+M to cycle modes", 8000)

    # Apply initial theme and badge
    try:
        from config.theme import apply_trading_mode_theme

        apply_trading_mode_theme(settings.TRADING_MODE)
        if hasattr(window, "panel_balance"):
            panel1 = window.panel_balance
            if hasattr(panel1, "set_trading_mode"):
                panel1.set_trading_mode(settings.TRADING_MODE)
    except Exception:
        pass


# Theme definitions (for reference)
THEME_DEFINITIONS = """
DEBUG Mode Theme (Grey/Silver Monochrome):
------------------------------------------
Purpose: Development and testing environment
Color Scheme: All grey and silver tones

Colors:
  - Background: #1E1E1E (Dark charcoal)
  - Secondary Background: #2D2D2D (Medium grey)
  - Text: #C0C0C0 (Silver)
  - Secondary Text: #808080 (Grey)
  - Borders: #404040 (Dark grey)
  - Accent: #B0B0B0 (Light grey)
  - Badge: #6B6B6B (Medium grey)
  - Grid Lines: #353535 (Very dark grey)
  - Hover: #3E3E3E (Slightly lighter grey)

Typography:
  - Monospace: Consolas, "Courier New"
  - Sans-serif: Segoe UI, Arial

Cell Styling:
  - No neon colors
  - Subtle shadows
  - Clean, minimal look
  - No borders (or very subtle 1px #353535)

LIVE Mode Theme (Gold/Black):
-----------------------------
Purpose: Real money trading (high attention)
Color Scheme: Black background, gold accents

Colors:
  - Background: #000000 (Pure black)
  - Text: #FFD700 (Gold)
  - Badge: #FFD700 (Gold, bold)
  - Borders: None
  - Alerts: #FF4444 (Red for warnings)

SIM Mode Theme (White/Neon Blue):
----------------------------------
Purpose: Simulated trading
Color Scheme: Light background, neon blue accents

Colors:
  - Background: #FFFFFF (White)
  - Text: #000000 (Black)
  - Badge: #00D4FF (Neon blue)
  - Cell Borders: #00D4FF 2px (Neon blue)
  - Accent: #0099CC (Dark cyan)
"""


if __name__ == "__main__":
    print("Mode Selector - Hotkey Method")
    print("=" * 50)
    print()
    print("Integration:")
    print("  1. Add to MainWindow.__init__:")
    print("     from utils.mode_selector import setup_mode_hotkey")
    print("     setup_mode_hotkey(self)")
    print()
    print("  2. Use Ctrl+Shift+M to cycle modes")
    print()
    print("Current Mode:", settings.TRADING_MODE)
    print()
    print(THEME_DEFINITIONS)
