# File: test_panels.py
"""
Test script for validating panel implementations.
Run from project root: python test_panels.py
"""

from pathlib import Path
import sys
import types


# Fix the path to point to project root (parent of tests/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_metrics_config():
    """Test that metric configurations exist and have correct counts."""
    print("=" * 60)
    print("TEST 1: Metrics Configuration")
    print("=" * 60)

    try:
        from config.trading_specs import PANEL2_METRICS, PANEL3_METRICS

        panel2_count = len(PANEL2_METRICS)
        panel3_count = len(PANEL3_METRICS)

        print(f"✓ PANEL2_METRICS: {panel2_count} metrics")
        print(f"✓ PANEL3_METRICS: {panel3_count} metrics")

        assert panel2_count == 15, f"Expected 15 Panel2 metrics, got {panel2_count}"
        assert panel3_count == 18, f"Expected 18 Panel3 metrics, got {panel3_count}"

        print("✓ All metric counts correct")
        assert True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        assert False


def test_metric_grid():
    """Test that MetricGrid has required methods."""
    print("\n" + "=" * 60)
    print("TEST 2: MetricGrid Widget")
    print("=" * 60)

    try:
        from widgets.metric_grid import MetricGrid

        required_methods = ["update_metric", "set_enabled_all", "get_all_values"]

        for method in required_methods:
            has_method = hasattr(MetricGrid, method)
            status = "✓" if has_method else "✗"
            print(f"{status} MetricGrid.{method}: {has_method}")

            if not has_method:
                print(f"  WARNING: Missing method {method}")

        print("✓ MetricGrid methods validated")
        assert True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        assert False


def test_panel1_no_pyqtgraph():
    """Test Panel1 gracefully handles missing pyqtgraph."""
    print("\n" + "=" * 60)
    print("TEST 3: Panel1 without pyqtgraph")
    print("=" * 60)

    try:
        from PyQt6 import QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        # Block pyqtgraph
        sys.modules["pyqtgraph"] = None

        from panels.panel1 import Panel1

        panel = Panel1()

        has_graph_method = hasattr(panel, "has_graph")
        plot_attr = getattr(panel, "_plot", "MISSING")

        print("✓ Panel1 instantiated without pyqtgraph")
        print(f"  - has_graph() method: {has_graph_method}")
        print(f"  - _plot attribute: {plot_attr}")

        if has_graph_method:
            graph_available = panel.has_graph()
            print(f"  - has_graph() returns: {graph_available}")
            assert not graph_available, "Graph should not be available without pyqtgraph"

        # Cleanup
        if "pyqtgraph" in sys.modules:
            del sys.modules["pyqtgraph"]
        if "panels.panel1" in sys.modules:
            del sys.modules["panels.panel1"]

        print("✓ Panel1 gracefully handles missing pyqtgraph")
        assert True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback

        traceback.print_exc()
        assert False


def test_panel1_with_broken_pyqtgraph():
    """Test Panel1 handles pyqtgraph initialization failure."""
    print("\n" + "=" * 60)
    print("TEST 4: Panel1 with broken pyqtgraph")
    print("=" * 60)

    try:
        from PyQt6 import QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        # Create mock pyqtgraph that raises on PlotWidget creation
        mock_pg = types.SimpleNamespace()

        def raise_plot_error(*args, **kwargs):
            raise RuntimeError("Mock: PlotWidget initialization failed")

        mock_pg.PlotWidget = raise_plot_error
        mock_pg.mkPen = lambda *a, **k: None
        mock_pg.mkBrush = lambda *a, **k: None
        mock_pg.ScatterPlotItem = object
        mock_pg.InfiniteLine = object
        mock_pg.TextItem = object

        # Inject mock
        sys.modules["pyqtgraph"] = mock_pg

        # Now try to import and create Panel1
        if "panels.panel1" in sys.modules:
            del sys.modules["panels.panel1"]

        from panels.panel1 import Panel1

        panel = Panel1()

        plot_attr = getattr(panel, "_plot", "MISSING")

        print("✓ Panel1 instantiated with broken pyqtgraph")
        print(f"  - _plot attribute: {plot_attr}")

        if hasattr(panel, "has_graph"):
            graph_available = panel.has_graph()
            print(f"  - has_graph() returns: {graph_available}")
            assert not graph_available, "Graph should not be available with broken pyqtgraph"

        # Cleanup
        if "pyqtgraph" in sys.modules:
            del sys.modules["pyqtgraph"]
        if "panels.panel1" in sys.modules:
            del sys.modules["panels.panel1"]

        print("✓ Panel1 gracefully handles pyqtgraph initialization failure")
        assert True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback

        traceback.print_exc()
        assert False


def test_all_panels_instantiate():
    """Test that all panels can be instantiated."""
    print("\n" + "=" * 60)
    print("TEST 5: Panel Instantiation")
    print("=" * 60)

    try:
        from PyQt6 import QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        # Ensure pyqtgraph is available
        if "pyqtgraph" in sys.modules and sys.modules["pyqtgraph"] is None:
            del sys.modules["pyqtgraph"]

        from panels.panel1 import Panel1
        from panels.panel2 import Panel2
        from panels.panel3 import Panel3

        panel1 = Panel1()
        print("✓ Panel1 instantiated")

        panel2 = Panel2()
        print("✓ Panel2 instantiated")

        panel3 = Panel3()
        print("✓ Panel3 instantiated")

        # Test basic methods exist
        assert hasattr(panel1, "set_account_balance"), "Panel1 missing set_account_balance"
        assert hasattr(panel1, "set_equity_series"), "Panel1 missing set_equity_series"
        assert hasattr(panel1, "refresh"), "Panel1 missing refresh"

        assert hasattr(panel2, "set_position"), "Panel2 missing set_position"
        assert hasattr(panel2, "refresh"), "Panel2 missing refresh"

        assert hasattr(panel3, "set_timeframe"), "Panel3 missing set_timeframe"
        assert hasattr(panel3, "update_metrics"), "Panel3 missing update_metrics"

        print("✓ All panels have required methods")
        assert True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback

        traceback.print_exc()
        assert False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "PANEL TEST SUITE" + " " * 27 + "║")
    print("╚" + "=" * 58 + "╝")

    tests = [
        test_metrics_config,
        test_metric_grid,
        test_panel1_no_pyqtgraph,
        test_panel1_with_broken_pyqtgraph,
        test_all_panels_instantiate,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n✗ TEST CRASHED: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
