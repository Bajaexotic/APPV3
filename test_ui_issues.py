#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test specific UI issues WITHOUT needing the full app.
Analyzes code to find why panels don't update.
"""

import sys
import os
from pathlib import Path

# Windows console Unicode fix
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def test_panel3_update_connection():
    """Check if Panel 3 is actually connected to receive updates."""
    print("\n" + "="*60)
    print("TEST: Panel 3 Update Connections")
    print("="*60)

    print("\n[1] Looking for Panel 3 signal connections...")

    try:
        with open("panels/panel3.py", "r") as f:
            panel3_code = f.read()

        # Check what signals Panel 3 listens to
        if "tradesChanged" in panel3_code:
            print("   ✓ Panel 3 has 'tradesChanged' signal")
        else:
            print("   ✗ Panel 3 does NOT listen to tradesChanged")

        if "timeframeChanged" in panel3_code:
            print("   ✓ Panel 3 has timeframeChanged signal")
        else:
            print("   ⚠ Panel 3 does NOT handle timeframeChanged")

        if "_load_metrics_for_timeframe" in panel3_code:
            print("   ✓ Panel 3 has _load_metrics_for_timeframe method")
        else:
            print("   ✗ Panel 3 missing metrics loading method")

    except Exception as e:
        print(f"   ✗ Error reading Panel 3: {e}")
        return False

    print("\n[2] Checking Panel 2 → Panel 3 connection...")

    try:
        with open("panels/panel2.py", "r") as f:
            panel2_code = f.read()

        # Check if Panel 2 emits trade closed signal
        if "tradesChanged.emit" in panel2_code:
            print("   ✓ Panel 2 emits 'tradesChanged' signal")
        else:
            print("   ✗ Panel 2 does NOT emit tradesChanged signal")

        if "notify_trade_closed" in panel2_code:
            print("   ✓ Panel 2 has notify_trade_closed method")
        else:
            print("   ✗ Panel 2 missing notify_trade_closed")

    except Exception as e:
        print(f"   ✗ Error reading Panel 2: {e}")
        return False

    print("\n[3] Checking app_manager for signal wiring...")

    try:
        with open("core/app_manager.py", "r") as f:
            app_code = f.read()

        if "panel3" in app_code.lower() and "panel2" in app_code.lower():
            print("   ✓ app_manager mentions both Panel 2 and Panel 3")

            if "tradesChanged.connect" in app_code:
                print("   ✓ app_manager connects tradesChanged signal")
            else:
                print("   ✗ app_manager does NOT connect tradesChanged")

            if "panel2" in app_code and "panel3" in app_code:
                # Look for specific connection pattern
                if "panel2.tradesChanged.connect(panel3" in app_code:
                    print("   ✓ Panel 2 → Panel 3 connection found")
                else:
                    print("   ⚠ Panel 2 → Panel 3 connection pattern not found")

        else:
            print("   ✗ app_manager doesn't mention both panels")

    except Exception as e:
        print(f"   ✗ Error reading app_manager: {e}")
        return False

    print("\n" + "="*60)
    return True


def test_balance_update_flow():
    """Check if balance update flows from trade → Panel 1."""
    print("\n" + "="*60)
    print("TEST: Balance Update Flow")
    print("="*60)

    print("\n[1] Checking trade_service.py for balance updates...")

    try:
        with open("services/trade_service.py", "r") as f:
            trade_code = f.read()

        if "set_balance_for_mode" in trade_code:
            print("   ✓ trade_service updates balance")
        else:
            print("   ✗ trade_service does NOT update balance")

        if "state.set_balance_for_mode" in trade_code:
            print("   ✓ trade_service calls set_balance_for_mode()")
        else:
            print("   ⚠ trade_service may not update state manager balance")

    except Exception as e:
        print(f"   ✗ Error reading trade_service: {e}")
        return False

    print("\n[2] Checking Panel 1 for balance display...")

    try:
        with open("panels/panel1.py", "r") as f:
            panel1_code = f.read()

        if "balance" in panel1_code.lower():
            print("   ✓ Panel 1 mentions balance")
        else:
            print("   ✗ Panel 1 doesn't handle balance")

        if "update_balance" in panel1_code:
            print("   ✓ Panel 1 has update_balance method")
        else:
            print("   ⚠ Panel 1 may not have update_balance method")

        if "balanceChanged" in panel1_code:
            print("   ✓ Panel 1 listens to balanceChanged signal")
        else:
            print("   ⚠ Panel 1 may not listen to balance changes")

    except Exception as e:
        print(f"   ✗ Error reading Panel 1: {e}")
        return False

    print("\n[3] Checking state_manager for balance signals...")

    try:
        with open("core/state_manager.py", "r") as f:
            state_code = f.read()

        if "balanceChanged" in state_code:
            print("   ✓ StateManager emits balanceChanged signal")
        else:
            print("   ✗ StateManager does NOT emit balanceChanged signal")

        if "set_balance_for_mode" in state_code:
            print("   ✓ StateManager has set_balance_for_mode()")
        else:
            print("   ✗ StateManager missing set_balance_for_mode()")

    except Exception as e:
        print(f"   ✗ Error reading state_manager: {e}")
        return False

    print("\n" + "="*60)
    return True


def test_graph_widget_visibility():
    """Check if graph widget is properly created and shown."""
    print("\n" + "="*60)
    print("TEST: Graph Widget Setup")
    print("="*60)

    print("\n[1] Checking if Panel 1 creates graph widget...")

    try:
        with open("panels/panel1.py", "r") as f:
            panel1_code = f.read()

        if "pg.PlotWidget" in panel1_code or "PlotWidget" in panel1_code:
            print("   ✓ Panel 1 creates PlotWidget")
        else:
            print("   ✗ Panel 1 does NOT create PlotWidget")

        if "pg.GraphicsView" in panel1_code or "GraphicsView" in panel1_code:
            print("   ✓ Panel 1 creates GraphicsView")
        else:
            print("   ⚠ Panel 1 may not use GraphicsView")

        if "addWidget" in panel1_code or "setCentralWidget" in panel1_code:
            print("   ✓ Panel 1 adds graph to layout")
        else:
            print("   ⚠ Panel 1 may not add graph to layout properly")

        if "setGeometry" in panel1_code or "setSize" in panel1_code:
            print("   ⚠ Panel 1 may be sizing graph")
        else:
            print("   ⚠ Panel 1 may not be sizing graph explicitly")

    except Exception as e:
        print(f"   ✗ Error reading Panel 1: {e}")
        return False

    print("\n[2] Checking for visibility issues...")

    try:
        with open("panels/panel1.py", "r") as f:
            panel1_code = f.read()

        if ".hide()" in panel1_code:
            print("   ⚠ Found .hide() calls - graph might be hidden")

        if "visible" in panel1_code.lower():
            print("   ✓ Visibility settings found")

        if "display:none" in panel1_code or "display: none" in panel1_code:
            print("   ✗ Found CSS display:none - graph hidden!")

    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "="*60)
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("UI ISSUE ANALYSIS - Code Review Only (No Dependencies Needed)")
    print("="*70)

    os.chdir("C:\\Users\\cgrah\\OneDrive\\Desktop\\APPSIERRA")

    all_ok = True

    all_ok &= test_panel3_update_connection()
    all_ok &= test_balance_update_flow()
    all_ok &= test_graph_widget_visibility()

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nBased on the above results:")
    print("- Check for ✗ marks - these are REAL ISSUES")
    print("- Check for ⚠ marks - these may be issues")
    print("\nFix these issues in the code, then test in the actual app.")

    sys.exit(0 if all_ok else 1)
