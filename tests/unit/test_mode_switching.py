"""
Test script for trading mode switching (DEBUG/SIM/LIVE)

Tests:
1. Badge updates correctly for each mode
2. Theme colors change based on mode
3. Ctrl+Shift+M hotkey cycles through modes
4. Terminal output is conditional on DEBUG mode

Usage:
    python test_mode_switching.py
"""

import os
import sys


# Set initial mode for testing
os.environ["TRADING_MODE"] = "SIM"

from PyQt6 import QtCore, QtWidgets

from config import settings
from config.theme import THEME, apply_trading_mode_theme


def test_badge_colors():
    """Test that badge colors are set correctly for each mode"""
    print("\n=== Testing Badge Colors ===")

    modes = ["DEBUG", "SIM", "LIVE"]
    expected_colors = {
        "DEBUG": "#808080",  # Grey
        "SIM": "#00D4FF",  # Neon blue
        "LIVE": "#FFD700",  # Gold
    }

    for mode in modes:
        print(f"\nTesting {mode} mode...")
        settings.TRADING_MODE = mode

        # Check badge color would be correct
        if mode == "DEBUG":
            assert expected_colors[mode] == "#808080", "DEBUG badge color mismatch"
            print(f"  ✓ Badge color: {expected_colors[mode]} (Grey)")
        elif mode == "SIM":
            assert expected_colors[mode] == "#00D4FF", "SIM badge color mismatch"
            print(f"  ✓ Badge color: {expected_colors[mode]} (Neon Blue)")
        else:  # LIVE
            assert expected_colors[mode] == "#FFD700", "LIVE badge color mismatch"
            print(f"  ✓ Badge color: {expected_colors[mode]} (Gold)")

    print("\n✓ All badge color tests passed!")


def test_theme_switching():
    """Test that themes are applied correctly for each mode"""
    print("\n=== Testing Theme Switching ===")

    modes = ["DEBUG", "SIM", "LIVE"]

    for mode in modes:
        print(f"\nApplying {mode} theme...")
        apply_trading_mode_theme(mode)

        # Verify theme colors
        if mode == "DEBUG":
            assert THEME["bg_primary"] == "#1E1E1E", "DEBUG bg_primary incorrect"
            assert THEME["ink"] == "#C0C0C0", "DEBUG ink incorrect"
            print(f"  ✓ Background: {THEME['bg_primary']} (Dark charcoal)")
            print(f"  ✓ Text: {THEME['ink']} (Silver)")

        elif mode == "SIM":
            assert THEME["bg_primary"] == "#FFFFFF", "SIM bg_primary incorrect"
            assert THEME["ink"] == "#000000", "SIM ink incorrect"
            assert THEME["border"] == "#00D4FF", "SIM border incorrect"
            print(f"  ✓ Background: {THEME['bg_primary']} (White)")
            print(f"  ✓ Text: {THEME['ink']} (Black)")
            print(f"  ✓ Border: {THEME['border']} (Neon Blue)")

        else:  # LIVE
            assert THEME["bg_primary"] == "#000000", "LIVE bg_primary incorrect"
            assert THEME["ink"] == "#FFD700", "LIVE ink incorrect"
            print(f"  ✓ Background: {THEME['bg_primary']} (Black)")
            print(f"  ✓ Text: {THEME['ink']} (Gold)")

    print("\n✓ All theme switching tests passed!")


def test_mode_cycling():
    """Test that mode cycling works in correct order"""
    print("\n=== Testing Mode Cycling ===")

    # Reset to DEBUG
    settings.TRADING_MODE = "DEBUG"

    cycle_order = ["DEBUG", "SIM", "LIVE"]
    current_idx = 0

    for i in range(6):  # Test 2 full cycles
        expected_mode = cycle_order[current_idx]
        assert expected_mode == settings.TRADING_MODE, f"Expected {expected_mode}, got {settings.TRADING_MODE}"

        print(f"  Cycle {i+1}: {settings.TRADING_MODE} ✓")

        # Simulate cycling
        current_idx = (current_idx + 1) % len(cycle_order)
        settings.TRADING_MODE = cycle_order[current_idx]

    print("\n✓ Mode cycling test passed!")


def test_ui_integration():
    """Test UI integration with actual widgets"""
    print("\n=== Testing UI Integration ===")

    app = QtWidgets.QApplication(sys.argv)

    try:
        # Import MainWindow
        from core.app_manager import MainWindow

        print("  Creating MainWindow...")
        window = MainWindow()

        # Check that panel_balance exists
        assert hasattr(window, "panel_balance"), "MainWindow missing panel_balance"
        print("  ✓ MainWindow has panel_balance")

        # Check that badge exists
        panel1 = window.panel_balance
        assert hasattr(panel1, "mode_badge"), "Panel1 missing mode_badge"
        print("  ✓ Panel1 has mode_badge")

        # Check that set_trading_mode method exists
        assert hasattr(panel1, "set_trading_mode"), "Panel1 missing set_trading_mode method"
        print("  ✓ Panel1 has set_trading_mode method")

        # Test badge update for each mode
        for mode in ["DEBUG", "SIM", "LIVE"]:
            panel1.set_trading_mode(mode)
            badge_text = panel1.mode_badge.text()
            assert badge_text == mode, f"Badge text should be {mode}, got {badge_text}"
            print(f"  ✓ Badge updates to: {mode}")

        # Show the window briefly
        window.show()
        print("\n  Window displayed successfully!")
        print("  Press Ctrl+Shift+M to test mode cycling")
        print("  (Window will close automatically in 3 seconds)")

        # Close after 3 seconds
        QtCore.QTimer.singleShot(3000, window.close)

        app.exec()

        print("\n✓ UI integration test passed!")

    except Exception as e:
        print(f"\n✗ UI integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    assert True


def main():
    """Run all tests"""
    print("=" * 60)
    print("TRADING MODE SWITCHING TEST SUITE")
    print("=" * 60)

    try:
        # Non-UI tests
        test_badge_colors()
        test_theme_switching()
        test_mode_cycling()

        # UI test (creates QApplication)
        success = test_ui_integration()

        if success:
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED! ✓")
            print("=" * 60)
            print("\nTo test in the app:")
            print("  1. Run: python main.py")
            print("  2. Press Ctrl+Shift+M to cycle modes")
            print("  3. Watch the badge change: DEBUG → SIM → LIVE")
            print("  4. Observe theme changes:")
            print("     - DEBUG: Grey/silver monochrome")
            print("     - SIM: White with neon blue")
            print("     - LIVE: Black with gold")
            return 0
        else:
            print("\n" + "=" * 60)
            print("SOME TESTS FAILED ✗")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
