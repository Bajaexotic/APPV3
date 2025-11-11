#!/usr/bin/env python
"""
Comprehensive system diagnostic for APPSIERRA.
Tests every critical component and identifies broken files.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

class Diagnostic:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def test(self, name, func):
        """Run a test and track results."""
        try:
            result = func()
            if result:
                self.passed.append(name)
                print(f"[PASS] {name}")
                return True
            else:
                self.failed.append(name)
                print(f"[FAIL] {name}")
                return False
        except Exception as e:
            self.failed.append(name)
            print(f"[FAIL] {name}: {e}")
            return False

    def warn(self, name, msg):
        """Record a warning."""
        self.warnings.append((name, msg))
        print(f"[WARN] {name}: {msg}")

    def report(self):
        """Print final report."""
        print("\n" + "="*60)
        print("DIAGNOSTIC REPORT")
        print("="*60)
        print(f"\nPassed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.failed:
            print("\n--- FAILED TESTS ---")
            for name in self.failed:
                print(f"  - {name}")

        if self.warnings:
            print("\n--- WARNINGS ---")
            for name, msg in self.warnings:
                print(f"  - {name}: {msg}")

        print("\n" + "="*60)
        return len(self.failed) == 0


def main():
    diag = Diagnostic()

    print("\n" + "="*60)
    print("APPSIERRA SYSTEM DIAGNOSTIC")
    print("="*60 + "\n")

    # ==== IMPORTS ====
    print("--- Testing Core Imports ---")

    diag.test("PyQt6", lambda: __import__('PyQt6'))
    diag.test("pyqtgraph", lambda: __import__('pyqtgraph'))

    diag.test("core.app_state", lambda: __import__('core.app_state', fromlist=['']))
    diag.test("core.state_manager", lambda: __import__('core.state_manager', fromlist=['']))
    diag.test("panels.panel1", lambda: __import__('panels.panel1', fromlist=['']))
    diag.test("panels.panel2", lambda: __import__('panels.panel2', fromlist=['']))
    diag.test("panels.panel3", lambda: __import__('panels.panel3', fromlist=['']))
    diag.test("widgets.metric_grid", lambda: __import__('widgets.metric_grid', fromlist=['']))

    diag.test("config.settings", lambda: __import__('config.settings', fromlist=['']))
    diag.test("config.theme", lambda: __import__('config.theme', fromlist=['']))

    # ==== STATE MANAGER ====
    print("\n--- Testing StateManager ---")

    def test_state_manager():
        from core.state_manager import StateManager
        sm = StateManager()
        # Check required attributes
        assert hasattr(sm, 'sim_balance'), "Missing sim_balance"
        assert hasattr(sm, 'live_balance'), "Missing live_balance"
        assert hasattr(sm, 'current_mode'), "Missing current_mode"
        assert hasattr(sm, 'balanceChanged'), "Missing balanceChanged signal"
        return True

    diag.test("StateManager attributes", test_state_manager)

    def test_balance_signal():
        from core.state_manager import StateManager
        sm = StateManager()
        called = False
        def callback(val):
            nonlocal called
            called = True
        sm.balanceChanged.connect(callback)
        sm.set_balance_for_mode("SIM", 10500.0)
        return called

    diag.test("StateManager.balanceChanged signal", test_balance_signal)

    # ==== PANEL 1 ====
    print("\n--- Testing Panel1 ---")

    def test_panel1_methods():
        from panels.panel1 import Panel1
        # Check for required methods
        assert hasattr(Panel1, '_wire_balance_signal'), "Missing _wire_balance_signal"
        assert hasattr(Panel1, '_on_balance_changed'), "Missing _on_balance_changed"
        return True

    diag.test("Panel1 signal methods", test_panel1_methods)

    # ==== PANEL 2 ====
    print("\n--- Testing Panel2 ---")

    def test_panel2_methods():
        from panels.panel2 import Panel2
        # Check for required methods
        assert hasattr(Panel2, 'notify_trade_closed'), "Missing notify_trade_closed"
        assert hasattr(Panel2, 'tradesChanged'), "Missing tradesChanged signal"
        return True

    diag.test("Panel2 methods and signals", test_panel2_methods)

    # ==== PANEL 3 ====
    print("\n--- Testing Panel3 ---")

    def test_panel3_methods():
        from panels.panel3 import Panel3
        assert hasattr(Panel3, 'update_metrics'), "Missing update_metrics"
        assert hasattr(Panel3, '_load_metrics_for_timeframe'), "Missing _load_metrics_for_timeframe"
        assert hasattr(Panel3, 'on_trade_closed'), "Missing on_trade_closed"
        assert hasattr(Panel3, 'display_empty_metrics'), "Missing display_empty_metrics"
        return True

    diag.test("Panel3 methods", test_panel3_methods)

    # ==== FILE CHECKS ====
    print("\n--- Checking Critical Files ---")

    critical_files = [
        "panels/panel1.py",
        "panels/panel2.py",
        "panels/panel3.py",
        "core/state_manager.py",
        "core/app_manager.py",
        "widgets/metric_grid.py",
        "config/settings.py",
    ]

    for file in critical_files:
        filepath = Path(__file__).parent / file
        if filepath.exists():
            size = filepath.stat().st_size
            if size > 0:
                print(f"[PASS] {file} exists ({size} bytes)")
            else:
                diag.failed.append(f"{file} - empty file")
                print(f"[FAIL] {file} - empty file")
        else:
            diag.failed.append(f"{file} - missing")
            print(f"[FAIL] {file} - MISSING")

    # ==== SYNTAX CHECK ====
    print("\n--- Checking Python Syntax ---")

    import py_compile

    for file in critical_files:
        filepath = Path(__file__).parent / file
        if filepath.exists():
            try:
                py_compile.compile(str(filepath), doraise=True)
                print(f"[PASS] {file} - valid syntax")
            except py_compile.PyCompileError as e:
                diag.failed.append(f"{file} - syntax error")
                print(f"[FAIL] {file} - SYNTAX ERROR: {e}")

    # ==== CONFIGURATION ====
    print("\n--- Checking Configuration ---")

    def test_config():
        from config.settings import DB_URL, THEME_MODE
        assert DB_URL is not None, "DB_URL is None"
        assert THEME_MODE is not None, "THEME_MODE is None"
        return True

    diag.test("Configuration settings", test_config)

    # ==== SIGNAL CONNECTIONS ====
    print("\n--- Checking Signal Integrity ---")

    def test_panel2_signal():
        from panels.panel2 import Panel2
        p = Panel2()
        assert hasattr(p, 'tradesChanged'), "Panel2 missing tradesChanged"
        # Try to connect
        callback_called = False
        def cb(*args):
            nonlocal callback_called
            callback_called = True
        p.tradesChanged.connect(cb)
        # Emit test signal
        p.tradesChanged.emit({})
        return callback_called

    try:
        result = test_panel2_signal()
        if result:
            print("[PASS] Panel2.tradesChanged signal works")
            diag.passed.append("Panel2.tradesChanged signal")
        else:
            print("[FAIL] Panel2.tradesChanged signal not firing")
            diag.failed.append("Panel2.tradesChanged signal")
    except Exception as e:
        print(f"[SKIP] Panel2 signal test (needs full app context): {e}")
        diag.warn("Panel2 signal test", "Requires full app context")

    # ==== FINAL REPORT ====
    success = diag.report()

    if success:
        print("\nSYSTEM READY FOR TESTING")
        return 0
    else:
        print("\nSYSTEM HAS ISSUES - SEE ABOVE")
        return 1


if __name__ == "__main__":
    sys.exit(main())
