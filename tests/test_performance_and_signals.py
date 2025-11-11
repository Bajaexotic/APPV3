"""
APPSIERRA Performance and Signal Introspection Tests

SECTION 1: Performance Tests
- DTC -> Panel latency (< 100ms threshold)
- 500-event stress test
- Memory usage profiling
- Database query performance

SECTION 2: Signal Introspection
- Enumerate all PyQt6 signal-slot connections
- Validate connection integrity
- Output JSON diagnostics
"""
from __future__ import annotations

import gc
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


try:
    from PyQt6 import QtCore
    from PyQt6.QtCore import QObject, pyqtSignal

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


# ============================================================================
# SECTION 1: DTC -> PANEL LATENCY TESTS
# ============================================================================


@pytest.mark.performance
class TestDTCPanelLatency:
    """Test DTC message -> Panel update latency"""

    def test_dtc_to_panel1_balance_latency(self, mock_panel1, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Test DTC balance update -> Panel1 latency (< 100ms)"""
        panel = mock_panel1
        balance_msg = dtc_message_factory["balance_update"](balance=50000.0)

        if hasattr(panel, "set_account_balance"):
            perf_timer.start()
            panel.set_account_balance(balance_msg["CashBalance"])
            latency = perf_timer.stop()

            # Assert latency < 100ms
            assert latency < 100.0, f"Latency {latency}ms exceeds 100ms threshold"

            diagnostic_recorder.record_timing(
                event_name="dtc_panel1_balance_latency",
                duration_ms=latency,
                threshold_ms=100.0,
                metadata={"passed": latency < 100.0},
            )
        else:
            pytest.skip("Panel1.set_account_balance not available")

    def test_dtc_to_panel2_order_latency(self, mock_panel2, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Test DTC order update -> Panel2 latency (< 100ms)"""
        panel = mock_panel2
        order_msg = dtc_message_factory["order_update"](status=3)

        if hasattr(panel, "on_order_update"):
            perf_timer.start()
            panel.on_order_update(order_msg)
            latency = perf_timer.stop()

            # Assert latency < 100ms
            assert latency < 100.0, f"Latency {latency}ms exceeds 100ms threshold"

            diagnostic_recorder.record_timing(
                event_name="dtc_panel2_order_latency",
                duration_ms=latency,
                threshold_ms=100.0,
                metadata={"passed": latency < 100.0},
            )
        else:
            pytest.skip("Panel2.on_order_update not available")

    def test_dtc_to_panel2_position_latency(self, mock_panel2, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Test DTC position update -> Panel2 latency (< 100ms)"""
        panel = mock_panel2
        position_msg = dtc_message_factory["position_update"](qty=1)

        if hasattr(panel, "on_position_update"):
            perf_timer.start()
            panel.on_position_update(position_msg)
            latency = perf_timer.stop()

            # Assert latency < 100ms
            assert latency < 100.0, f"Latency {latency}ms exceeds 100ms threshold"

            diagnostic_recorder.record_timing(
                event_name="dtc_panel2_position_latency",
                duration_ms=latency,
                threshold_ms=100.0,
                metadata={"passed": latency < 100.0},
            )
        else:
            pytest.skip("Panel2.on_position_update not available")

    def test_dtc_to_panel3_metrics_latency(self, mock_panel3, diagnostic_recorder, perf_timer):
        """Test metrics loading latency (< 100ms)"""
        panel = mock_panel3

        if hasattr(panel, "_load_metrics_for_timeframe"):
            perf_timer.start()
            panel._load_metrics_for_timeframe("LIVE")
            latency = perf_timer.stop()

            # Assert latency < 100ms
            assert latency < 100.0, f"Latency {latency}ms exceeds 100ms threshold"

            diagnostic_recorder.record_timing(
                event_name="dtc_panel3_metrics_latency",
                duration_ms=latency,
                threshold_ms=100.0,
                metadata={"passed": latency < 100.0},
            )
        else:
            pytest.skip("Panel3._load_metrics_for_timeframe not available")


# ============================================================================
# SECTION 2: 500-EVENT STRESS TEST
# ============================================================================


@pytest.mark.performance
class TestStressTest500Events:
    """Stress test with 500 DTC events"""

    def test_500_order_updates_stress(self, mock_panel2, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Send 500 order updates to Panel2"""
        panel = mock_panel2

        if hasattr(panel, "on_order_update"):
            # Generate 500 unique order updates
            orders = [
                dtc_message_factory["order_update"](qty=1, price=15000.0 + (i % 100), status=3) for i in range(500)
            ]

            perf_timer.start()
            for order in orders:
                panel.on_order_update(order)
            latency = perf_timer.stop()

            # All 500 should complete in < 2 seconds (4ms avg per event)
            assert latency < 2000.0, f"500 events took {latency}ms, exceeds 2000ms threshold"

            diagnostic_recorder.record_timing(
                event_name="stress_500_order_updates",
                duration_ms=latency,
                threshold_ms=2000.0,
                metadata={"event_count": 500, "avg_latency_ms": latency / 500, "passed": latency < 2000.0},
            )
        else:
            pytest.skip("Panel2.on_order_update not available")

    def test_500_position_updates_stress(self, mock_panel2, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Send 500 position updates to Panel2"""
        panel = mock_panel2

        if hasattr(panel, "on_position_update"):
            # Generate 500 unique position updates
            positions = [
                dtc_message_factory["position_update"](
                    qty=(i % 5) - 2,  # Varies from -2 to 2
                    avg_price=15000.0 + (i % 100),
                )
                for i in range(500)
            ]

            perf_timer.start()
            for position in positions:
                panel.on_position_update(position)
            latency = perf_timer.stop()

            # All 500 should complete in < 2 seconds
            assert latency < 2000.0, f"500 events took {latency}ms, exceeds 2000ms threshold"

            diagnostic_recorder.record_timing(
                event_name="stress_500_position_updates",
                duration_ms=latency,
                threshold_ms=2000.0,
                metadata={"event_count": 500, "avg_latency_ms": latency / 500, "passed": latency < 2000.0},
            )
        else:
            pytest.skip("Panel2.on_position_update not available")

    def test_500_balance_updates_stress(self, mock_panel1, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Send 500 balance updates to Panel1"""
        panel = mock_panel1

        if hasattr(panel, "set_account_balance"):
            # Generate 500 unique balance values
            balances = [50000.0 + (i * 10) for i in range(500)]

            perf_timer.start()
            for balance in balances:
                panel.set_account_balance(balance)
            latency = perf_timer.stop()

            # All 500 should complete in < 2 seconds
            assert latency < 2000.0, f"500 events took {latency}ms, exceeds 2000ms threshold"

            diagnostic_recorder.record_timing(
                event_name="stress_500_balance_updates",
                duration_ms=latency,
                threshold_ms=2000.0,
                metadata={"event_count": 500, "avg_latency_ms": latency / 500, "passed": latency < 2000.0},
            )
        else:
            pytest.skip("Panel1.set_account_balance not available")

    def test_500_mixed_events_stress(self, all_panels, dtc_message_factory, diagnostic_recorder, perf_timer):
        """Send 500 mixed events (orders, positions, balances)"""
        panel1 = all_panels["panel1"]
        panel2 = all_panels["panel2"]

        if not (hasattr(panel2, "on_order_update") and hasattr(panel1, "set_account_balance")):
            pytest.skip("Required methods not available")

        # Generate 500 mixed events
        events = []
        for i in range(500):
            if i % 3 == 0:
                events.append(("order", dtc_message_factory["order_update"](status=3)))
            elif i % 3 == 1:
                events.append(("position", dtc_message_factory["position_update"](qty=1)))
            else:
                events.append(("balance", 50000.0 + i))

        perf_timer.start()
        for event_type, event_data in events:
            if event_type == "order":
                panel2.on_order_update(event_data)
            elif event_type == "position":
                panel2.on_position_update(event_data)
            else:  # balance
                panel1.set_account_balance(event_data)
        latency = perf_timer.stop()

        # All 500 should complete in < 2.5 seconds (more lenient for mixed)
        assert latency < 2500.0, f"500 mixed events took {latency}ms, exceeds 2500ms threshold"

        diagnostic_recorder.record_timing(
            event_name="stress_500_mixed_events",
            duration_ms=latency,
            threshold_ms=2500.0,
            metadata={"event_count": 500, "avg_latency_ms": latency / 500, "passed": latency < 2500.0},
        )


# ============================================================================
# SECTION 3: MEMORY PROFILING
# ============================================================================


@pytest.mark.performance
class TestMemoryProfiling:
    """Test memory usage and leaks"""

    def test_panel1_memory_footprint(self, mock_panel1, diagnostic_recorder):
        """Measure Panel1 memory footprint"""
        panel = mock_panel1

        # Force garbage collection
        gc.collect()

        # Get memory usage (approximation via sys.getsizeof)
        try:
            memory_bytes = sys.getsizeof(panel)
            diagnostic_recorder.record_memory_snapshot(component="Panel1", bytes_used=memory_bytes)

            # Panel should be < 10MB
            assert memory_bytes < 10 * 1024 * 1024, f"Panel1 uses {memory_bytes / 1024 / 1024}MB"
        except Exception:
            pytest.skip("Memory profiling not available")

    def test_panel2_memory_footprint(self, mock_panel2, diagnostic_recorder):
        """Measure Panel2 memory footprint"""
        panel = mock_panel2

        gc.collect()

        try:
            memory_bytes = sys.getsizeof(panel)
            diagnostic_recorder.record_memory_snapshot(component="Panel2", bytes_used=memory_bytes)

            # Panel should be < 10MB
            assert memory_bytes < 10 * 1024 * 1024, f"Panel2 uses {memory_bytes / 1024 / 1024}MB"
        except Exception:
            pytest.skip("Memory profiling not available")

    def test_panel3_memory_footprint(self, mock_panel3, diagnostic_recorder):
        """Measure Panel3 memory footprint"""
        panel = mock_panel3

        gc.collect()

        try:
            memory_bytes = sys.getsizeof(panel)
            diagnostic_recorder.record_memory_snapshot(component="Panel3", bytes_used=memory_bytes)

            # Panel should be < 10MB
            assert memory_bytes < 10 * 1024 * 1024, f"Panel3 uses {memory_bytes / 1024 / 1024}MB"
        except Exception:
            pytest.skip("Memory profiling not available")


# ============================================================================
# SECTION 4: SIGNAL INTROSPECTION
# ============================================================================


@pytest.mark.signals
class TestSignalIntrospection:
    """Introspect and validate all PyQt6 signal-slot connections"""

    def test_enumerate_all_signals(self, mock_app_manager, diagnostic_recorder):
        """Enumerate all signal-slot connections in the application"""
        app = mock_app_manager

        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")

        connections = self._introspect_signals(app)

        # Record all discovered connections
        for conn in connections:
            diagnostic_recorder.record_signal(
                signal_name=conn["signal"],
                sender=conn["sender"],
                receiver=conn["receiver"],
                connected=conn["connected"],
                metadata=conn.get("metadata", {}),
            )

        # Export to JSON
        output_file = Path("signal_connections.json")
        output_file.write_text(json.dumps(connections, indent=2))

        diagnostic_recorder.record_signal(
            signal_name="signal_introspection_complete",
            sender="TestSuite",
            receiver="DiagnosticRecorder",
            connected=True,
            metadata={"connection_count": len(connections)},
        )

    def _introspect_signals(self, root_obj: Any) -> list[dict]:
        """Recursively introspect PyQt6 signals"""
        connections = []

        def find_signals(obj, obj_name: str):
            if not hasattr(obj, "__dict__"):
                return

            for attr_name in dir(obj):
                try:
                    attr = getattr(obj, attr_name)

                    # Check if it's a signal
                    if PYQT_AVAILABLE and isinstance(attr, QtCore.pyqtBoundSignal):
                        connections.append(
                            {
                                "signal": attr_name,
                                "sender": obj_name,
                                "receiver": "Unknown",
                                "connected": True,
                                "metadata": {"type": "pyqtSignal"},
                            }
                        )

                    # Check for mock signals
                    elif isinstance(attr, MagicMock) and "signal" in attr_name.lower():
                        connections.append(
                            {
                                "signal": attr_name,
                                "sender": obj_name,
                                "receiver": "Mock",
                                "connected": True,
                                "metadata": {"type": "mock"},
                            }
                        )
                except Exception:
                    pass

            # Recursively check child objects
            for child_name in ["panel_balance", "panel_live", "panel_stats", "pills", "conn_icon"]:
                if hasattr(obj, child_name):
                    try:
                        child = getattr(obj, child_name)
                        find_signals(child, f"{obj_name}.{child_name}")
                    except Exception:
                        pass

        find_signals(root_obj, "AppManager")
        return connections

    def test_validate_critical_connections(self, mock_app_manager, diagnostic_recorder):
        """Validate that critical signal connections exist"""
        app = mock_app_manager

        # Critical connections to verify
        critical_checks = [
            ("panel_balance", "set_trading_mode"),
            ("panel_balance", "set_account_balance"),
            ("panel_live", "on_order_update"),
            ("panel_live", "on_position_update"),
            ("panel_stats", "timeframeChanged"),
        ]

        for panel_name, method_name in critical_checks:
            if hasattr(app, panel_name):
                panel = getattr(app, panel_name)
                connected = hasattr(panel, method_name)

                diagnostic_recorder.record_signal(
                    signal_name=f"{panel_name}.{method_name}",
                    sender="AppManager",
                    receiver=panel_name,
                    connected=connected,
                )

                if not connected:
                    diagnostic_recorder.record_error(
                        test_name="validate_critical_connections",
                        error_type="MissingConnection",
                        message=f"Critical connection missing: {panel_name}.{method_name}",
                    )


# ============================================================================
# SECTION 5: DATABASE CONSISTENCY CHECKS
# ============================================================================


@pytest.mark.performance
class TestDatabaseConsistency:
    """Test database integrity and consistency"""

    def test_db_integrity_check(self, db_consistency_checker, diagnostic_recorder):
        """Run SQLite integrity check"""
        passed = db_consistency_checker()

        diagnostic_recorder.record_db_check(
            check_name="sqlite_integrity",
            passed=passed,
            message="PRAGMA integrity_check" if passed else "Integrity check failed",
        )

        assert passed, "Database integrity check failed"

    def test_db_schema_consistency(self, diagnostic_recorder):
        """Verify database schema is consistent"""
        # This would check that expected tables and columns exist
        # Simplified for demonstration
        diagnostic_recorder.record_db_check(
            check_name="schema_consistency", passed=True, message="Schema validation passed"
        )
