#!/usr/bin/env python
"""
Debug script to trace trade close data flow between panels.
Run this to understand where data goes when a trade closes.

Set environment variable to enable detailed logging:
set DEBUG_DTC=1
python DEBUG_TRADE_FLOW.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Enable debug mode
os.environ["DEBUG_DTC"] = "1"

from PyQt6 import QtWidgets, QtCore
from panels.panel1 import Panel1
from panels.panel2 import Panel2
from panels.panel3 import Panel3
from core.app_state import get_state_manager
from utils.logger import get_logger

log = get_logger(__name__)

class DebugTracer:
    """Traces signal flow between panels."""

    def __init__(self, panel1, panel2, panel3):
        self.panel1 = panel1
        self.panel2 = panel2
        self.panel3 = panel3
        self.events = []

    def connect_tracers(self):
        """Connect to all signals to trace their flow."""
        log.info("="*60)
        log.info("STARTING SIGNAL TRACING")
        log.info("="*60)

        # Trace Panel 2 tradesChanged signal
        if hasattr(self.panel2, 'tradesChanged'):
            self.panel2.tradesChanged.connect(self._on_panel2_trade_closed)
            log.info("[TRACER] Connected to Panel2.tradesChanged")
        else:
            log.warn("[TRACER] Panel2 missing tradesChanged signal!")

        # Trace StateManager balance signal
        state = get_state_manager()
        if state and hasattr(state, 'balanceChanged'):
            state.balanceChanged.connect(self._on_balance_changed)
            log.info("[TRACER] Connected to StateManager.balanceChanged")
        else:
            log.warn("[TRACER] StateManager missing balanceChanged signal!")

        # Trace Panel 3 timeframe changes
        if hasattr(self.panel3, 'timeframeChanged'):
            self.panel3.timeframeChanged.connect(self._on_panel3_timeframe_changed)
            log.info("[TRACER] Connected to Panel3.timeframeChanged")

    def _on_panel2_trade_closed(self, trade_payload):
        """Called when Panel 2 emits tradesChanged."""
        log.info("="*60)
        log.info("[TRACER] PANEL 2 TRADE CLOSED EVENT")
        log.info("="*60)
        log.info(f"  Trade Payload Keys: {list(trade_payload.keys())}")
        log.info(f"  Trade Data: {trade_payload}")
        log.info(f"  PnL: {trade_payload.get('realized_pnl')}")
        self.events.append(("panel2_trade_closed", trade_payload))

    def _on_balance_changed(self, balance):
        """Called when StateManager emits balanceChanged."""
        log.info("="*60)
        log.info("[TRACER] STATE MANAGER BALANCE CHANGED")
        log.info("="*60)
        log.info(f"  New Balance: ${balance}")
        self.events.append(("balance_changed", balance))

    def _on_panel3_timeframe_changed(self, timeframe):
        """Called when Panel 3 changes timeframe."""
        log.info("="*60)
        log.info("[TRACER] PANEL 3 TIMEFRAME CHANGED")
        log.info("="*60)
        log.info(f"  New Timeframe: {timeframe}")
        self.events.append(("panel3_timeframe_changed", timeframe))

    def report(self):
        """Print event trace report."""
        log.info("\n" + "="*60)
        log.info("EVENT TRACE REPORT")
        log.info("="*60)
        for i, (event_type, data) in enumerate(self.events):
            log.info(f"{i+1}. {event_type}: {data}")


def test_trade_flow():
    """Simulate closing a trade and watch the signal flow."""

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    log.info("\nCreating panels...")
    panel1 = Panel1()
    panel2 = Panel2()
    panel3 = Panel3()

    # Set up cross-panel references
    panel1.set_stats_panel(panel3)
    panel2.set_stats_panel(panel3)
    panel3.set_live_panel(panel2)

    log.info("Panels created and cross-linked")

    # Create tracer
    tracer = DebugTracer(panel1, panel2, panel3)
    tracer.connect_tracers()

    log.info("\n" + "="*60)
    log.info("SIMULATING TRADE CLOSE")
    log.info("="*60)

    # Simulate closing a trade
    test_trade = {
        "symbol": "F.US.MESM25",
        "side": "LONG",
        "qty": 1,
        "entry_price": 100.0,
        "exit_price": 105.0,
        "realized_pnl": 500.0,
        "entry_time": None,
        "exit_time": None,
        "commissions": 0.0,
        "r_multiple": None,
        "mae": None,
        "mfe": None,
        "account": "Sim1",
    }

    log.info(f"Emitting Panel 2 tradesChanged with: {test_trade}")
    panel2.tradesChanged.emit(test_trade)

    # Process events
    log.info("\nProcessing Qt events...")
    for _ in range(10):
        app.processEvents()

    tracer.report()

    log.info("\n" + "="*60)
    log.info("CHECKING PANEL STATES AFTER TRADE")
    log.info("="*60)

    # Check Panel 1 balance
    if hasattr(panel1, 'lbl_balance'):
        log.info(f"Panel 1 Balance Label Text: {panel1.lbl_balance.text()}")
    else:
        log.warn("Panel 1 missing lbl_balance")

    # Check Panel 3 metrics
    if hasattr(panel3, 'metric_grid'):
        log.info(f"Panel 3 has metric_grid: {panel3.metric_grid is not None}")
    else:
        log.warn("Panel 3 missing metric_grid")

    log.info("\n" + "="*60)
    log.info("DEBUG TRACE COMPLETE")
    log.info("="*60)


if __name__ == "__main__":
    test_trade_flow()
