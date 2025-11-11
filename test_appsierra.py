#!/usr/bin/env python
"""
PyTest suite for APPSIERRA system diagnostics.
Run with: pytest test_appsierra.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


class TestImports:
    """Test all critical imports."""

    def test_pyqt6(self):
        import PyQt6
        assert PyQt6 is not None

    def test_pyqtgraph(self):
        import pyqtgraph
        assert pyqtgraph is not None

    def test_core_app_state(self):
        from core.app_state import get_state_manager
        assert get_state_manager is not None

    def test_core_state_manager(self):
        from core.state_manager import StateManager
        assert StateManager is not None

    def test_panels_panel1(self):
        from panels.panel1 import Panel1
        assert Panel1 is not None

    def test_panels_panel2(self):
        from panels.panel2 import Panel2
        assert Panel2 is not None

    def test_panels_panel3(self):
        from panels.panel3 import Panel3
        assert Panel3 is not None

    def test_widgets_metric_grid(self):
        from widgets.metric_grid import MetricGrid
        assert MetricGrid is not None

    def test_config_settings(self):
        from config.settings import DB_URL
        assert DB_URL is not None


class TestStateManager:
    """Test StateManager functionality."""

    def test_state_manager_creation(self):
        from core.state_manager import StateManager
        sm = StateManager()
        assert sm is not None

    def test_state_manager_balance_attributes(self):
        from core.state_manager import StateManager
        sm = StateManager()
        assert hasattr(sm, "sim_balance")
        assert hasattr(sm, "live_balance")
        assert hasattr(sm, "current_mode")

    def test_state_manager_balance_signal_exists(self):
        from core.state_manager import StateManager
        sm = StateManager()
        assert hasattr(sm, "balanceChanged")

    def test_balance_changed_signal_emission(self):
        from core.state_manager import StateManager
        sm = StateManager()

        callback_called = False
        received_value = None

        def on_balance_changed(value):
            nonlocal callback_called, received_value
            callback_called = True
            received_value = value

        sm.balanceChanged.connect(on_balance_changed)
        sm.balanceChanged.emit(10500.0)

        assert callback_called, "Callback was not called"
        assert received_value == 10500.0, f"Expected 10500.0, got {received_value}"

    def test_set_balance_for_mode_emits_signal(self):
        from core.state_manager import StateManager
        sm = StateManager()

        callback_called = False
        received_value = None

        def on_balance_changed(value):
            nonlocal callback_called, received_value
            callback_called = True
            received_value = value

        sm.balanceChanged.connect(on_balance_changed)
        sm.set_balance_for_mode("SIM", 11000.0)

        assert callback_called, "Signal not emitted by set_balance_for_mode"
        assert received_value == 11000.0


class TestPanel1:
    """Test Panel1 methods."""

    def test_panel1_has_wire_balance_signal(self):
        from panels.panel1 import Panel1
        assert hasattr(Panel1, "_wire_balance_signal")

    def test_panel1_has_on_balance_changed(self):
        from panels.panel1 import Panel1
        assert hasattr(Panel1, "_on_balance_changed")

    def test_panel1_methods_callable(self):
        from panels.panel1 import Panel1
        assert callable(getattr(Panel1, "_wire_balance_signal"))
        assert callable(getattr(Panel1, "_on_balance_changed"))


class TestPanel2:
    """Test Panel2 methods."""

    def test_panel2_has_notify_trade_closed(self):
        from panels.panel2 import Panel2
        assert hasattr(Panel2, "notify_trade_closed")

    def test_panel2_has_trades_changed_signal(self):
        from panels.panel2 import Panel2
        assert hasattr(Panel2, "tradesChanged")


class TestPanel3:
    """Test Panel3 methods."""

    def test_panel3_has_update_metrics(self):
        from panels.panel3 import Panel3
        assert hasattr(Panel3, "update_metrics")

    def test_panel3_has_load_metrics_for_timeframe(self):
        from panels.panel3 import Panel3
        assert hasattr(Panel3, "_load_metrics_for_timeframe")

    def test_panel3_has_on_trade_closed(self):
        from panels.panel3 import Panel3
        assert hasattr(Panel3, "on_trade_closed")

    def test_panel3_has_display_empty_metrics(self):
        from panels.panel3 import Panel3
        assert hasattr(Panel3, "display_empty_metrics")


class TestFileIntegrity:
    """Test that critical files exist and are valid."""

    @pytest.mark.parametrize("filepath", [
        "panels/panel1.py",
        "panels/panel2.py",
        "panels/panel3.py",
        "core/state_manager.py",
        "core/app_manager.py",
        "widgets/metric_grid.py",
        "config/settings.py",
    ])
    def test_file_exists(self, filepath):
        file = Path(__file__).parent / filepath
        assert file.exists(), f"File does not exist: {filepath}"
        assert file.stat().st_size > 0, f"File is empty: {filepath}"

    @pytest.mark.parametrize("filepath", [
        "panels/panel1.py",
        "panels/panel2.py",
        "panels/panel3.py",
        "core/state_manager.py",
        "core/app_manager.py",
        "widgets/metric_grid.py",
    ])
    def test_file_syntax_valid(self, filepath):
        import py_compile
        file = Path(__file__).parent / filepath
        try:
            py_compile.compile(str(file), doraise=True)
        except Exception as e:
            pytest.fail(f"Syntax error in {filepath}: {e}")


class TestConfiguration:
    """Test configuration."""

    def test_db_url_configured(self):
        from config.settings import DB_URL
        assert DB_URL is not None, "DB_URL is not configured"
        assert len(DB_URL) > 0, "DB_URL is empty"

    def test_theme_configured(self):
        from config.theme import THEME
        assert THEME is not None
        assert len(THEME) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
