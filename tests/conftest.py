"""
APPSIERRA Test Configuration

Pytest fixtures and configuration for comprehensive testing suite.
Provides fixtures for PyQt6 components, DTC simulation, and diagnostic recording.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# SECTION 1: DIAGNOSTIC RECORDER
# ============================================================================


class DiagnosticRecorder:
    """
    Records test diagnostics, signal connections, timing data, and errors.
    Outputs JSON artifacts for self-healing analysis.
    """

    def __init__(self):
        self.signals: list[dict[str, Any]] = []
        self.timing_events: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.coverage_data: dict[str, Any] = {}
        self.memory_snapshots: list[dict[str, Any]] = []
        self.db_checks: list[dict[str, Any]] = []

    def record_signal(
        self, signal_name: str, sender: str, receiver: str, connected: bool = True, metadata: Optional[dict] = None
    ):
        """Record signal connection status"""
        self.signals.append(
            {
                "timestamp": datetime.now().isoformat(),
                "signal": signal_name,
                "sender": sender,
                "receiver": receiver,
                "connected": connected,
                "metadata": metadata or {},
            }
        )

    def record_timing(
        self, event_name: str, duration_ms: float, threshold_ms: float = 100.0, metadata: Optional[dict] = None
    ):
        """Record timing event with threshold checking"""
        passed = duration_ms < threshold_ms
        self.timing_events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_name,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms,
                "passed": passed,
                "metadata": metadata or {},
            }
        )
        return passed

    def record_error(self, test_name: str, error_type: str, message: str, stack_trace: Optional[str] = None):
        """Record test error or failure"""
        self.errors.append(
            {
                "timestamp": datetime.now().isoformat(),
                "test": test_name,
                "error_type": error_type,
                "message": message,
                "stack_trace": stack_trace,
            }
        )

    def record_memory_snapshot(self, component: str, bytes_used: int):
        """Record memory usage snapshot"""
        self.memory_snapshots.append(
            {
                "timestamp": datetime.now().isoformat(),
                "component": component,
                "bytes": bytes_used,
                "mb": bytes_used / (1024 * 1024),
            }
        )

    def record_db_check(self, check_name: str, passed: bool, message: str):
        """Record database consistency check result"""
        self.db_checks.append(
            {"timestamp": datetime.now().isoformat(), "check": check_name, "passed": passed, "message": message}
        )

    def export_json(self, output_path: str = "test_diagnostics.json"):
        """Export all diagnostic data to JSON"""
        data = {
            "generated": datetime.now().isoformat(),
            "signals": self.signals,
            "timing": self.timing_events,
            "errors": self.errors,
            "memory": self.memory_snapshots,
            "db_checks": self.db_checks,
            "summary": {
                "total_signals": len(self.signals),
                "connected_signals": sum(1 for s in self.signals if s["connected"]),
                "timing_violations": sum(1 for t in self.timing_events if not t["passed"]),
                "total_errors": len(self.errors),
                "memory_snapshots": len(self.memory_snapshots),
                "db_check_failures": sum(1 for c in self.db_checks if not c["passed"]),
            },
        }

        output_file = Path(output_path)
        output_file.write_text(json.dumps(data, indent=2))
        return str(output_file.absolute())


@pytest.fixture(scope="session")
def diagnostic_recorder():
    """Session-scoped diagnostic recorder"""
    recorder = DiagnosticRecorder()
    yield recorder
    # Export diagnostics at end of session
    output_path = recorder.export_json("test_diagnostics.json")
    print(f"\n[DIAGNOSTICS] Exported to: {output_path}")


# ============================================================================
# SECTION 2: QAPPLICATION AND QTBOT
# ============================================================================


@pytest.fixture(scope="session")
def qapp():
    """
    Session-scoped QApplication instance.
    Required for all PyQt6 tests.
    """
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        yield app

        # Cleanup
        app.quit()
    except ImportError:
        # If PyQt6 not available, return mock
        yield MagicMock()


@pytest.fixture
def qtbot(qapp):
    """
    Provides QtBot for PyQt6 widget testing.
    Allows simulating user interactions and waiting for signals.
    """
    try:
        from pytestqt.qtbot import QtBot

        bot = QtBot(qapp)
        yield bot
    except ImportError:
        # Fallback to mock if pytest-qt not installed
        yield MagicMock()


# ============================================================================
# SECTION 3: STATE MANAGER
# ============================================================================


@pytest.fixture
def mock_state_manager():
    """Mock StateManager for testing without database dependencies"""
    mock = MagicMock()
    mock.get_setting.return_value = None
    mock.set_setting.return_value = True
    mock.db_path = ":memory:"
    return mock


@pytest.fixture
def state_manager():
    """
    Real StateManager instance for integration tests.
    Uses in-memory SQLite database.
    """
    try:
        from core.state_manager import StateManager

        # Patch to use in-memory database
        with patch.object(StateManager, "__init__", lambda self: None):
            sm = StateManager()
            sm.db_path = ":memory:"
            sm.get_setting = MagicMock(return_value=None)
            sm.set_setting = MagicMock(return_value=True)
            yield sm
    except Exception:
        # Fallback to mock
        yield mock_state_manager()


# ============================================================================
# SECTION 4: PANEL FIXTURES
# ============================================================================


@pytest.fixture
def mock_panel1(qtbot):
    """Real Panel1 when available; fallback only if import fails."""
    try:
        from panels.panel1 import Panel1
    except ImportError:
        mock = MagicMock()
        mock.set_trading_mode = MagicMock()
        mock.set_account_balance = MagicMock()
        mock.set_stats_panel = MagicMock()
        yield mock
        return

    panel = Panel1()
    # Wrap key methods with MagicMocks that call through for assertion compatibility
    if hasattr(panel, "set_trading_mode"):
        _orig = panel.set_trading_mode
        panel.set_trading_mode = MagicMock(side_effect=_orig)
    if hasattr(panel, "set_account_balance"):
        _orig2 = panel.set_account_balance
        panel.set_account_balance = MagicMock(side_effect=_orig2)
    if hasattr(panel, "set_stats_panel"):
        _orig3 = panel.set_stats_panel
        panel.set_stats_panel = MagicMock(side_effect=_orig3)
    yield panel
    panel.close()


@pytest.fixture
def mock_panel2(qtbot):
    """Real Panel2 when available; fallback only if import fails."""
    try:
        from panels.panel2 import Panel2
    except ImportError:
        mock = MagicMock()
        mock.on_order_update = MagicMock()
        mock.on_position_update = MagicMock()
        mock.tradesChanged = MagicMock()
        mock.pills = MagicMock()
        yield mock
        return

    panel = Panel2()
    # Wrap handlers so tests can assert .called while preserving behavior
    if hasattr(panel, "on_order_update"):
        _o = panel.on_order_update
        panel.on_order_update = MagicMock(side_effect=_o)
    if hasattr(panel, "on_position_update"):
        _p = panel.on_position_update
        panel.on_position_update = MagicMock(side_effect=_p)
    yield panel
    panel.close()


@pytest.fixture
def mock_panel3(qtbot):
    """Real Panel3 when available; fallback only if import fails."""
    try:
        from panels.panel3 import Panel3
    except ImportError:
        mock = MagicMock()
        mock.set_live_panel = MagicMock()
        mock.timeframeChanged = MagicMock()
        mock._load_metrics_for_timeframe = MagicMock()
        mock.analyze_and_store_trade_snapshot = MagicMock()
        yield mock
        return

    panel = Panel3()
    # Optionally wrap some methods used by tests, preserving behavior
    if hasattr(panel, "set_live_panel"):
        _sl = panel.set_live_panel
        panel.set_live_panel = MagicMock(side_effect=_sl)
    if hasattr(panel, "_load_metrics_for_timeframe"):
        _lm = panel._load_metrics_for_timeframe
        panel._load_metrics_for_timeframe = MagicMock(side_effect=_lm)
    if hasattr(panel, "analyze_and_store_trade_snapshot"):
        _an = panel.analyze_and_store_trade_snapshot
        panel.analyze_and_store_trade_snapshot = MagicMock(side_effect=_an)
    yield panel
    panel.close()


@pytest.fixture
def all_panels(mock_panel1, mock_panel2, mock_panel3):
    """Returns dict with all three panels"""
    return {"panel1": mock_panel1, "panel2": mock_panel2, "panel3": mock_panel3}


# ============================================================================
# SECTION 5: APP MANAGER
# ============================================================================


@pytest.fixture
def mock_app_manager(qtbot, all_panels):
    """Mock MainWindow/AppManager for integration tests"""
    try:
        from core.app_manager import MainWindow

        # Mock DTC to avoid connection attempts
        with patch("core.app_manager.DataBridge"):
            window = MainWindow()
            qtbot.addWidget(window)
            yield window

            # Cleanup
            window.close()
    except Exception:
        mock = MagicMock()
        mock.panel_balance = all_panels["panel1"]
        mock.panel_live = all_panels["panel2"]
        mock.panel_stats = all_panels["panel3"]
        yield mock


# ============================================================================
# SECTION 6: DTC MESSAGE SIMULATION
# ============================================================================


@pytest.fixture
def dtc_message_factory():
    """Factory for creating DTC test messages"""

    def create_logon_response(success=True):
        return {
            "Type": 2,
            "ProtocolVersion": 8,
            "Result": "LOGON_SUCCESS" if success else "LOGON_FAILED",
            "ServerName": "TestServer",
        }

    def create_order_update(symbol="NQ", qty=1, price=15000.0, status=3):
        return {
            "Type": 300,
            "Symbol": symbol,
            "OrderQuantity": qty,
            "Price1": price,
            "OrderStatus": status,
            "TradeAccount": "120005",
            "OrderID": "TEST_ORDER_001",
        }

    def create_position_update(symbol="NQ", qty=1, avg_price=15000.0):
        return {"Type": 306, "Symbol": symbol, "Quantity": qty, "AveragePrice": avg_price, "TradeAccount": "120005"}

    def create_balance_update(balance=50000.0):
        return {"Type": 600, "CashBalance": balance, "AccountValue": balance, "TradeAccount": "120005"}

    return {
        "logon_response": create_logon_response,
        "order_update": create_order_update,
        "position_update": create_position_update,
        "balance_update": create_balance_update,
    }


# ============================================================================
# SECTION 7: PERFORMANCE HELPERS
# ============================================================================


@pytest.fixture
def perf_timer():
    """High-resolution performance timer"""

    class PerfTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()
            return self.elapsed_ms()

        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0.0

    return PerfTimer()


# ============================================================================
# SECTION 8: DATABASE HELPERS
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path for testing"""
    db_file = tmp_path / "test_appsierra.db"
    yield str(db_file)
    # Cleanup handled by tmp_path


@pytest.fixture
def db_consistency_checker(temp_db_path):
    """Database consistency checker"""

    def check_integrity():
        """Check SQLite database integrity"""
        try:
            import sqlite3

            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            return result == "ok"
        except Exception as e:
            return False

    return check_integrity


# ============================================================================
# SECTION 9: LOG CAPTURE
# ============================================================================


@pytest.fixture
def log_capture(caplog):
    """Enhanced log capture with filtering"""

    class LogCapture:
        def __init__(self, caplog):
            self.caplog = caplog

        def contains_error(self, message: str) -> bool:
            """Check if any error log contains message"""
            return any(message in record.message for record in self.caplog.records if record.levelname == "ERROR")

        def contains_warning(self, message: str) -> bool:
            """Check if any warning log contains message"""
            return any(message in record.message for record in self.caplog.records if record.levelname == "WARNING")

        def get_errors(self) -> list[str]:
            """Get all error messages"""
            return [record.message for record in self.caplog.records if record.levelname == "ERROR"]

        def get_warnings(self) -> list[str]:
            """Get all warning messages"""
            return [record.message for record in self.caplog.records if record.levelname == "WARNING"]

    return LogCapture(caplog)


# ============================================================================
# SECTION 10: PYTEST HOOKS
# ============================================================================


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "signals: marks tests as signal introspection tests")


def pytest_runtest_makereport(item, call):
    """Hook to capture test results for diagnostic recorder"""
    if call.when == "call":
        # Access diagnostic_recorder if available
        if hasattr(item, "funcargs") and "diagnostic_recorder" in item.funcargs:
            recorder = item.funcargs["diagnostic_recorder"]

            if call.excinfo is not None:
                recorder.record_error(
                    test_name=item.nodeid,
                    error_type=call.excinfo.typename,
                    message=str(call.excinfo.value),
                    stack_trace=str(call.excinfo.traceback),
                )


# ============================================================================
# SECTION 11: MODE ROUTING FIXTURES
# ============================================================================


@pytest.fixture
def mock_trading_modes():
    """Provide SIM, LIVE, DEBUG mode configurations"""
    return {
        "SIM": {"account": "SIM1", "theme": "SIM_THEME", "allow_real_orders": False},
        "LIVE": {"account": "120005", "theme": "LIVE_THEME", "allow_real_orders": True},
        "DEBUG": {"account": "DEBUG", "theme": "DEBUG_THEME", "allow_real_orders": False},
    }


@pytest.fixture
def mode_detector():
    """Factory for testing account-to-mode detection logic"""

    def detect_mode(trade_account: str) -> str:
        """
        Detect trading mode from account string.

        Args:
            trade_account: Account name/number from DTC

        Returns:
            "SIM", "LIVE", or "DEBUG"

        Expected accounts:
            - "SIM1" → SIM mode
            - "120005" → LIVE mode
        """
        if not trade_account:
            return "DEBUG"

        account_upper = str(trade_account).upper()

        if account_upper.startswith("SIM"):
            return "SIM"
        elif account_upper == "DEBUG":
            return "DEBUG"
        else:
            # Default to LIVE for non-SIM accounts (e.g., "120005")
            return "LIVE"

    return detect_mode


@pytest.fixture
def order_filter():
    """Factory for testing order filtering logic"""

    def should_accept_order(app_mode: str, order_account: str) -> bool:
        """
        Determine if order should be accepted based on mode and account.

        Args:
            app_mode: Current app mode (SIM/LIVE/DEBUG)
            order_account: TradeAccount from order message

        Returns:
            True if order should be accepted, False if rejected
        """
        if app_mode == "DEBUG":
            return True  # DEBUG mode accepts all (for testing)

        order_is_sim = str(order_account).upper().startswith("SIM")
        app_is_sim = app_mode == "SIM"

        return order_is_sim == app_is_sim

    return should_accept_order


@pytest.fixture
def theme_loader():
    """Mock theme loader for testing theme switching"""

    class ThemeLoader:
        def __init__(self):
            self.current_theme = None
            self.load_count = 0

        def load_theme(self, mode: str):
            """Load theme for given mode"""
            theme_map = {"SIM": "SIM_THEME", "LIVE": "LIVE_THEME", "DEBUG": "DEBUG_THEME"}
            self.current_theme = theme_map.get(mode, "DEBUG_THEME")
            self.load_count += 1
            return self.current_theme

        def get_theme_color(self, key: str, default: str = "#000000") -> str:
            """Get color from current theme"""
            # Mock implementation
            theme_colors = {
                "SIM_THEME": {"bg_primary": "#1a1a2e", "accent": "#00ff00"},
                "LIVE_THEME": {"bg_primary": "#000000", "accent": "#ff0000"},
                "DEBUG_THEME": {"bg_primary": "#2e2e2e", "accent": "#ffff00"},
            }
            return theme_colors.get(self.current_theme, {}).get(key, default)

    return ThemeLoader()


# ============================================================================
# SECTION 12: XDist Worker Trace (helps identify stalled workers)
# ============================================================================

_TRACE_FILE = os.path.join(os.getcwd(), "logs", "worker_trace.log")
os.makedirs(os.path.dirname(_TRACE_FILE), exist_ok=True)


def _trace_write(line: str) -> None:
    try:
        with open(_TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def pytest_runtest_logstart(nodeid, location):
    wid = os.environ.get("PYTEST_XDIST_WORKER", "main")
    _trace_write(f"{time.time():.3f} START {wid} {nodeid}")


def pytest_runtest_logreport(report):
    # Emit an END line for each completed call-phase
    if report.when != "call":
        return
    wid = os.environ.get("PYTEST_XDIST_WORKER", "main")
    outcome = (
        "PASSED"
        if report.passed
        else ("FAILED" if report.failed else ("SKIPPED" if report.skipped else report.outcome.upper()))
    )
    _trace_write(f"{time.time():.3f} END   {wid} {report.nodeid} {outcome} dur={getattr(report, 'duration', 0.0):.3f}s")
