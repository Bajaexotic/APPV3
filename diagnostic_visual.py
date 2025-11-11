#!/usr/bin/env python
"""Comprehensive visual diagnostic for Panel 1 graph rendering"""

import sys
import time
from PyQt6 import QtWidgets

print("\n" + "="*80)
print("COMPREHENSIVE PANEL 1 VISUAL DIAGNOSTIC")
print("="*80)

# Initialize Qt app
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

# Test 1: Check theme system
print("\n[TEST 1] Theme System Configuration")
print("-" * 80)
try:
    from config.theme import THEME, DEBUG_THEME, SIM_THEME, LIVE_THEME
    print("[OK] Theme modules imported")

    print("\nDEBUG_THEME colors:")
    print(f"  bg_primary: {DEBUG_THEME.get('bg_primary')}")
    print(f"  bg_secondary: {DEBUG_THEME.get('bg_secondary')}")
    print(f"  bg_panel: {DEBUG_THEME.get('bg_panel')}")
    print(f"  ink: {DEBUG_THEME.get('ink')}")
    print(f"  pnl_pos_color: {DEBUG_THEME.get('pnl_pos_color')}")
    print(f"  pnl_neg_color: {DEBUG_THEME.get('pnl_neg_color')}")
    print(f"  pnl_neu_color: {DEBUG_THEME.get('pnl_neu_color')}")

    print("\nSIM_THEME colors:")
    print(f"  bg_primary: {SIM_THEME.get('bg_primary')}")
    print(f"  bg_secondary: {SIM_THEME.get('bg_secondary')}")
    print(f"  ink: {SIM_THEME.get('ink')}")

    print("\nLIVE_THEME colors:")
    print(f"  bg_primary: {LIVE_THEME.get('bg_primary')}")
    print(f"  bg_secondary: {LIVE_THEME.get('bg_secondary')}")
    print(f"  ink: {LIVE_THEME.get('ink')}")

    print("\nCurrent THEME (active):")
    print(f"  bg_primary: {THEME.get('bg_primary')}")
    print(f"  bg_secondary: {THEME.get('bg_secondary')}")
    print(f"  ink: {THEME.get('ink')}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 2: Check color contrast
print("\n[TEST 2] Color Contrast Analysis")
print("-" * 80)
try:
    from utils.theme_helpers import normalize_color
    from config.theme import ColorTheme

    neutral_color = ColorTheme.pnl_color_from_direction(None)
    positive_color = ColorTheme.pnl_color_from_direction(True)
    negative_color = ColorTheme.pnl_color_from_direction(False)

    bg_secondary = normalize_color(THEME.get("bg_secondary"))

    print(f"Background (bg_secondary): {bg_secondary}")
    print(f"Neutral PnL color: {neutral_color}")
    print(f"Positive PnL color: {positive_color}")
    print(f"Negative PnL color: {negative_color}")

    # Check if colors are same (invisible)
    if bg_secondary.lower() == neutral_color.lower():
        print("[WARNING] Background and neutral color are IDENTICAL - line will be invisible!")
    if bg_secondary.lower() == positive_color.lower():
        print("[WARNING] Background and positive color are IDENTICAL - line will be invisible!")
    if bg_secondary.lower() == negative_color.lower():
        print("[WARNING] Background and negative color are IDENTICAL - line will be invisible!")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 3: Panel1 instantiation and visual properties
print("\n[TEST 3] Panel1 Widget Hierarchy & Visibility")
print("-" * 80)
try:
    from panels.panel1 import Panel1

    panel = Panel1()
    print("[OK] Panel1 created")

    # Check main widget
    print(f"\nPanel1 Properties:")
    print(f"  isVisible: {panel.isVisible()}")
    print(f"  size: {panel.size().width()}x{panel.size().height()}")
    print(f"  minimumSize: {panel.minimumSize().width()}x{panel.minimumSize().height()}")
    print(f"  maximumSize: {panel.maximumSize().width()}x{panel.maximumSize().height()}")

    # Check graph container
    print(f"\nGraph Container (MaskedFrame):")
    print(f"  isVisible: {panel.graph_container.isVisible()}")
    print(f"  size: {panel.graph_container.size().width()}x{panel.graph_container.size().height()}")
    print(f"  minimumSize: {panel.minimumSize().width()}x{panel.minimumSize().height()}")
    print(f"  bg_color set to: {panel.graph_container._bg_color}")

    # Check plot widget
    if panel._plot:
        print(f"\nPlot Widget:")
        print(f"  isVisible: {panel._plot.isVisible()}")
        print(f"  size: {panel._plot.size().width()}x{panel._plot.size().height()}")
        print(f"  background: {panel._plot.getBackground()}")
        print(f"  parent: {type(panel._plot.parent()).__name__}")

        # Check plot item
        plot_item = panel._plot.getPlotItem()
        print(f"\nPlot Item:")
        try:
            left_visible = plot_item.axes['left']['item'].isVisible()
            bottom_visible = plot_item.axes['bottom']['item'].isVisible()
            print(f"  left axis visible: {left_visible}")
            print(f"  bottom axis visible: {bottom_visible}")
        except:
            print(f"  axes hidden (expected)")
    else:
        print("[ERROR] Plot widget is None!")

    # Check line
    if panel._line:
        print(f"\nEquity Line:")
        xs, ys = panel._line.getData()
        point_count = len(xs) if xs is not None else 0
        print(f"  data points: {point_count}")
        print(f"  pen: {panel._line.opts}")
    else:
        print("[ERROR] Line is None!")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 4: Add test data and check rendering
print("\n[TEST 4] Test Data & Rendering")
print("-" * 80)
try:
    from panels.panel1 import Panel1

    panel = Panel1()

    # Add test data
    now = time.time()
    print("Adding 25 test data points...")
    for i in range(25):
        balance = 50000.0 + (i * 100)
        panel.update_equity_series_from_balance(balance, 'SIM')

    # Check data was added
    pts = panel._filtered_points_for_current_tf()
    print(f"[OK] Added {len(pts)} points to equity curve")

    if pts:
        print(f"  First point: {pts[0]}")
        print(f"  Last point: {pts[-1]}")
        print(f"  P&L up: {panel._pnl_up}")
        print(f"  P&L value: {panel._pnl_val}")

    # Test P&L setting
    panel.set_pnl_for_timeframe(2500.0, 5.0, True)
    print(f"\n[OK] Set P&L - pnl_up={panel._pnl_up}, color should be green")

    # Check line has data
    if panel._line:
        xs, ys = panel._line.getData()
        count = len(xs) if xs is not None else 0
        print(f"\n[OK] Line has {count} data points")
        if xs is not None and len(xs) > 0:
            print(f"  X range: {xs[0]:.0f} to {xs[-1]:.0f}")
            print(f"  Y range: {ys[0]:.2f} to {ys[-1]:.2f}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check hover elements
print("\n[TEST 5] Hover Elements")
print("-" * 80)
try:
    from panels.panel1 import Panel1

    panel = Panel1()

    print(f"Hover line (_hover_seg): {panel._hover_seg is not None}")
    if panel._hover_seg:
        print(f"  type: {type(panel._hover_seg).__name__}")
        print(f"  isVisible: {panel._hover_seg.isVisible()}")

    print(f"Hover text (_hover_text): {panel._hover_text is not None}")
    if panel._hover_text:
        print(f"  type: {type(panel._hover_text).__name__}")
        print(f"  isVisible: {panel._hover_text.isVisible()}")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 6: Check viewport settings
print("\n[TEST 6] PyQtGraph Viewport Settings")
print("-" * 80)
try:
    from panels.panel1 import Panel1

    panel = Panel1()

    if panel._vb:
        print(f"ViewBox exists: True")
        view_range = panel._vb.viewRange()
        print(f"  X range: {view_range[0]}")
        print(f"  Y range: {view_range[1]}")
    else:
        print("[ERROR] ViewBox is None!")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 7: MaskedFrame rendering
print("\n[TEST 7] MaskedFrame Rendering")
print("-" * 80)
try:
    from panels.panel1 import Panel1

    panel = Panel1()

    print(f"Graph container type: {type(panel.graph_container).__name__}")
    print(f"Has mask: {panel.graph_container.mask() is not None}")
    print(f"Background color: {panel.graph_container._bg_color}")

except Exception as e:
    print(f"[ERROR] {e}")

# Summary
print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80 + "\n")
