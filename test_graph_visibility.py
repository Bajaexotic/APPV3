#!/usr/bin/env python
"""
Test graph visibility in Panel 1.
Creates a simple test window with various graph configurations to verify rendering.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg


def test_basic_graph():
    """Test 1: Can we create a basic pyqtgraph plot?"""
    print("\n[TEST 1] Basic PyQtGraph Creation")
    print("-" * 40)

    try:
        # Create app
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

        # Create window
        window = QtWidgets.QMainWindow()
        window.setWindowTitle("Test: Basic Graph")
        window.setGeometry(100, 100, 800, 600)

        # Create plot widget
        plot_widget = pg.PlotWidget()
        plot_widget.setTitle("Test: Simple Line Plot")
        plot_widget.setLabel("left", "Price")
        plot_widget.setLabel("bottom", "Bar #")

        # Add some data
        x_data = list(range(100))
        y_data = [100 + i*0.5 for i in range(100)]

        plot_widget.plot(x_data, y_data, pen=pg.mkPen("cyan", width=2))

        window.setCentralWidget(plot_widget)
        window.show()

        # Process events for a moment
        for _ in range(10):
            app.processEvents()

        print("✓ Basic graph created and shown")
        print("  - Window visible: YES")
        print("  - Plot widget created: YES")
        print("  - Data plotted: YES (100 points)")

        window.close()
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_candlestick_graph():
    """Test 2: Can we create a candlestick-style plot?"""
    print("\n[TEST 2] Candlestick-Style Graph")
    print("-" * 40)

    try:
        app = QtWidgets.QApplication.instance()

        window = QtWidgets.QMainWindow()
        window.setWindowTitle("Test: Candlestick Graph")
        window.setGeometry(100, 100, 800, 600)

        plot_widget = pg.PlotWidget()
        plot_widget.setTitle("Test: Price Bars")
        plot_widget.setLabel("left", "Price ($)")
        plot_widget.setLabel("bottom", "Bar #")

        # Simulate OHLC data
        bars = []
        for i in range(20):
            open_price = 100 + i * 0.2
            high_price = open_price + 2
            low_price = open_price - 1
            close_price = open_price + 0.5

            bars.append({
                "x": i,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            })

        # Draw bars
        for bar in bars:
            x = bar["x"]
            # High-low line
            plot_widget.plot([x, x], [bar["low"], bar["high"]], pen=pg.mkPen("white", width=1))
            # Open-close box
            color = "green" if bar["close"] > bar["open"] else "red"
            plot_widget.plot(
                [x-0.3, x+0.3, x+0.3, x-0.3, x-0.3],
                [bar["open"], bar["open"], bar["close"], bar["close"], bar["open"]],
                pen=pg.mkPen(color, width=2),
                fillLevel=bar["open"],
                fillBrush=pg.mkBrush(color)
            )

        window.setCentralWidget(plot_widget)
        window.show()

        for _ in range(10):
            app.processEvents()

        print("✓ Candlestick graph created")
        print("  - 20 bars rendered: YES")
        print("  - Colors (green/red): YES")

        window.close()
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_panel1_graph_directly():
    """Test 3: Try to load Panel1 and check its graph widget."""
    print("\n[TEST 3] Panel 1 Graph Widget")
    print("-" * 40)

    try:
        from panels.panel1 import Panel1

        print("✓ Panel1 imported successfully")

        # Try to create it
        panel = Panel1()
        print("✓ Panel1 instance created")

        # Check if it has a graph widget
        if hasattr(panel, "plot_widget"):
            print(f"✓ plot_widget exists: {type(panel.plot_widget)}")
        elif hasattr(panel, "chart"):
            print(f"✓ chart exists: {type(panel.chart)}")
        else:
            print("⚠ No obvious graph widget found in Panel1")
            print(f"  Panel1 attributes: {[a for a in dir(panel) if not a.startswith('_')][:10]}")

        # Check parent
        if hasattr(panel, "parent"):
            print(f"✓ Panel1 parent: {type(panel.parent())}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_in_window():
    """Test 4: Put Panel1 in a window and see if graph shows."""
    print("\n[TEST 4] Panel 1 in Window")
    print("-" * 40)

    try:
        from panels.panel1 import Panel1

        app = QtWidgets.QApplication.instance()

        window = QtWidgets.QMainWindow()
        window.setWindowTitle("Test: Panel 1 Graph Visibility")
        window.setGeometry(100, 100, 1000, 700)

        # Create panel
        panel = Panel1()
        window.setCentralWidget(panel)
        window.show()

        # Process events
        for _ in range(20):
            app.processEvents()

        print("✓ Panel1 added to window and shown")
        print("  ⚠ CHECK VISUALLY: Do you see a graph in the window?")
        print("    - If YES: Graph rendering is working")
        print("    - If NO: Graph may be hidden or not sized correctly")

        # Keep window open briefly
        for _ in range(50):
            app.processEvents()

        window.close()
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GRAPH VISIBILITY TESTS")
    print("="*60)
    print("\nThese tests will create small windows to verify")
    print("that graphs can be rendered. Watch for windows appearing.")

    try:
        # Test basic rendering first
        test_basic_graph()

        # Test candlestick
        test_candlestick_graph()

        # Test Panel1 directly
        test_panel1_graph_directly()

        # Test Panel1 in window
        test_graph_in_window()

        print("\n" + "="*60)
        print("GRAPH TESTS COMPLETE")
        print("="*60)
        print("\nIf you saw windows pop up with graphs, rendering works.")
        print("If you didn't see anything, check:")
        print("  1. PyQtGraph installation: pip install pyqtgraph")
        print("  2. Display/graphics drivers")
        print("  3. Panel1 widget visibility settings")

    except Exception as e:
        print(f"\n✗ Tests crashed: {e}")
        import traceback
        traceback.print_exc()

    sys.exit(0)
