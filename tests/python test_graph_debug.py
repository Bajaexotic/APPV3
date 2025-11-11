# File: test_graph_debug.py
"""
Standalone test to debug Panel1 graph display issues.
Run: python test_graph_debug.py
"""

from pathlib import Path
import sys
import time


# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg


print(f"PyQtGraph version: {getattr(pg, '__version__', 'unknown')}")

# Test 1: Basic pyqtgraph functionality
print("\n" + "=" * 60)
print("TEST 1: Basic PyQtGraph")
print("=" * 60)

app = QtWidgets.QApplication([])

# Create simple test plot
test_plot = pg.PlotWidget()
test_plot.setWindowTitle("Basic PyQtGraph Test")
test_plot.setBackground("#0A0A0A")

# Add test data
x_data = list(range(100))
y_data = [i**2 for i in range(100)]
test_plot.plot(x_data, y_data, pen=pg.mkPen("g", width=2))

test_plot.resize(600, 400)
test_plot.show()
print("✓ Basic plot created and shown")

# Process events to render
app.processEvents()
time.sleep(0.5)
test_plot.close()

# Test 2: Panel1 with sample data
print("\n" + "=" * 60)
print("TEST 2: Panel1 Graph")
print("=" * 60)

from panels.panel1 import Panel1


panel1 = Panel1()
panel1.setWindowTitle("Panel1 Test")
panel1.resize(800, 600)

# Check graph initialization
print("✓ Panel1 created")
print(f"  - has_graph: {panel1.has_graph() if hasattr(panel1, 'has_graph') else 'N/A'}")
print(f"  - _plot exists: {panel1._plot is not None}")
print(f"  - _line exists: {panel1._line is not None}")
print(f"  - _endpoint exists: {panel1._endpoint is not None}")

if panel1._plot is None:
    print("\n✗ PROBLEM: Graph not initialized!")
    print("  Check _init_graph() method for errors")
    sys.exit(1)

# Generate realistic test data (NO MOCK DATA - use live account data instead)
# This test now expects data to be provided by the app
current_time = time.time()
test_points = []
# Removed mock data generation - test should use actual account data

print(f"\n✓ Generated {len(test_points)} test data points")
if test_points:
    print(f"  Time range: {test_points[0][0]:.0f} to {test_points[-1][0]:.0f}")
    print(f"  Value range: ${test_points[0][1]:.2f} to ${test_points[-1][1]:.2f}")
else:
    print("  (No mock data - expecting live account data)")

# Set data
if test_points:
    panel1.set_equity_series(test_points)
else:
    print("  Skipping data set - no mock data provided")
print("✓ Data set to panel")
print(f"  Stored points: {len(panel1._equity_points)}")

# Check if line has data
if panel1._line:
    line_data = panel1._line.getData()
    print(f"  Line X data: {len(line_data[0]) if line_data[0] is not None else 0} points")
    print(f"  Line Y data: {len(line_data[1]) if line_data[1] is not None else 0} points")

    if line_data[0] is None or len(line_data[0]) == 0:
        print("\n✗ PROBLEM: Line has no data!")
        print("  Check set_equity_series() -> _line.setData() calls")
    else:
        print("✓ Line has data")

# Check visibility
if panel1._plot:
    print(f"\n✓ Plot widget visibility: {panel1._plot.isVisible()}")
    if panel1._line:
        print(f"  Line visibility: {panel1._line.isVisible()}")
    if panel1._endpoint:
        print(f"  Endpoint visibility: {panel1._endpoint.isVisible()}")

# Set additional panel data
panel1.set_account_balance(10500.0)
panel1.set_pnl_for_timeframe(500.0, 5.0, True)
panel1.set_mode_live(False)
panel1.set_connection_status(True)

print("\n✓ Panel metadata set")

# Show panel
panel1.show()
print("\n✓ Panel shown - Look for window!")
print("  Window title: 'Panel1 Test'")
print("  Expected: Graph with green upward line")
print("\n  Press Ctrl+C in terminal to close...")

# Run event loop briefly
timer = QtCore.QTimer()
timer.timeout.connect(lambda: print(".", end="", flush=True))
timer.start(1000)


# Auto-close after 10 seconds or wait for manual close
def auto_close():
    print("\n\n✓ Test complete - closing window")
    app.quit()


QtCore.QTimer.singleShot(10000, auto_close)

try:
    app.exec()
except KeyboardInterrupt:
    print("\n\n✓ Test interrupted by user")
    sys.exit(0)
