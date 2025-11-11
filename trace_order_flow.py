#!/usr/bin/env python
"""
Order Flow Tracer
Traces order data from DTC → data_bridge → MessageRouter → Panels
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

# Enable debug output
import os
os.environ["DEBUG_SIGNAL"] = "1"
os.environ["DEBUG_DATA"] = "1"

import structlog

# Setup logging to see the trace
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger(__name__)


def trace_order_path():
    """Hook into all signal points and trace order flow"""
    print("\n" + "="*80)
    print("ORDER FLOW TRACER - Starting monitoring")
    print("="*80)
    print("\nFlow Path:")
    print("  DTC Server -> data_bridge -> signal_order -> MessageRouter -> Panel2 -> Panel3")
    print("\nListening for order updates...")
    print("="*80 + "\n")

    trace_log = []

    def log_event(stage: str, data: dict):
        """Log each stage of the order flow"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{ts}] {stage:25s} | {data}"
        print(msg)
        trace_log.append(msg)

    # Hook 1: data_bridge signals
    try:
        from core.data_bridge import signal_order, signal_balance, signal_position

        def on_order_signal(sender, **kwargs):
            log_event("[SIGNAL] signal_order", kwargs)

        def on_balance_signal(sender, **kwargs):
            log_event("[SIGNAL] signal_balance", kwargs)

        def on_position_signal(sender, **kwargs):
            log_event("[SIGNAL] signal_position", kwargs)

        signal_order.connect(on_order_signal, weak=False)
        signal_balance.connect(on_balance_signal, weak=False)
        signal_position.connect(on_position_signal, weak=False)

        log_event("[OK] Hooked", {"component": "data_bridge signals"})
    except Exception as e:
        log.error("Failed to hook data_bridge", error=str(e))

    # Hook 2: MessageRouter
    try:
        from core.message_router import MessageRouter

        original_on_order = MessageRouter._on_order_update

        def traced_on_order(self, payload: dict):
            log_event("[ROUTER] MessageRouter", {"method": "_on_order_update", "payload": payload})
            return original_on_order(self, payload)

        MessageRouter._on_order_update = traced_on_order
        log_event("[OK] Hooked", {"component": "MessageRouter"})
    except Exception as e:
        log.error("Failed to hook MessageRouter", error=str(e))

    # Hook 3: Panel2 (Live Trading)
    try:
        from panels.panel2 import Panel2

        original_on_order_update = Panel2.on_order_update

        def traced_panel2_order(self, payload: dict):
            log_event("[PANEL2] Panel2", {"method": "on_order_update", "symbol": payload.get("Symbol", "?")})
            return original_on_order_update(self, payload)

        Panel2.on_order_update = traced_panel2_order
        log_event("[OK] Hooked", {"component": "Panel2.on_order_update"})
    except Exception as e:
        log.error("Failed to hook Panel2", error=str(e))

    # Hook 4: Panel3 (Stats)
    try:
        from panels.panel3 import Panel3

        # Panel3 listens to tradesChanged signal from Panel2
        log_event("[OK] Monitor", {"component": "Panel3 (listens to tradesChanged)"})
    except Exception as e:
        log.error("Failed to hook Panel3", error=str(e))

    return trace_log


if __name__ == "__main__":
    # Install hooks first
    trace_log = trace_order_path()

    print("\n[OK] All hooks installed. Starting main application...\n")

    # Now run the main app
    try:
        from main import main
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("TRACE COMPLETE")
        print("="*80)
        for line in trace_log[-20:]:  # Show last 20 events
            print(line)
        sys.exit(0)
    except Exception as e:
        log.error("Main app error", error=str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
