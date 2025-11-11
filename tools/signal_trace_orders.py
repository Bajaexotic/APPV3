#!/usr/bin/env python
"""
Signal Trace Orders - Live Order Propagation Diagnostic
Verifies end-to-end order flow: Blinker → MessageRouter → marshal_to_qt_thread → Panel2

Usage:
    In main.py:
    if os.getenv("DEBUG_DTC", "1") == "1":
        from tools.signal_trace_orders import attach_order_trace
        attach_order_trace()
"""
from __future__ import annotations

import functools
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional


# ==================== Configuration ====================
LOG_FILE = Path(__file__).parent.parent / "logs" / "signal_trace_orders.log"
TRACE_PREFIX = "[TRACE]"


# ==================== Logger ====================
class OrderTraceLogger:
    """Simple logger that writes to both console and file."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO") -> None:
        """Log message to console and file."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] {TRACE_PREFIX} [{level}] {message}"

        # Print to console
        print(formatted)

        # Write to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception as e:
            print(f"{TRACE_PREFIX} [ERROR] Failed to write to log file: {e}")

    def trace(self, message: str) -> None:
        """Log a trace message."""
        self.log(message, "TRACE")

    def error(self, message: str, exc: Optional[Exception] = None) -> None:
        """Log an error with optional exception details."""
        self.log(message, "ERROR")
        if exc:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.log(f"Exception details:\n{tb}", "ERROR")


# ==================== Global Logger Instance ====================
logger = OrderTraceLogger(LOG_FILE)


# ==================== Trace Hooks ====================
def attach_order_trace() -> None:
    """
    Attach order signal tracer to monitor Blinker → Router → Qt → Panel2 flow.
    Safe to call - will gracefully handle missing imports.
    """
    logger.trace("Order signal tracer initializing...")

    # Step 1: Hook Blinker signal_order
    if not _hook_blinker_signal():
        logger.error("Failed to hook Blinker signal_order - continuing anyway")

    # Step 2: Monkey-patch MessageRouter
    if not _patch_message_router():
        logger.error("Failed to patch MessageRouter - continuing anyway")

    # Step 3: Monkey-patch marshal_to_qt_thread
    if not _patch_qt_marshal():
        logger.error("Failed to patch marshal_to_qt_thread - continuing anyway")

    # Step 4: Monkey-patch Panel2.on_order_update
    if not _patch_panel2():
        logger.error("Failed to patch Panel2.on_order_update - continuing anyway")

    logger.trace("Order signal tracer active (Blinker->Qt->Panel2)")


def _hook_blinker_signal() -> bool:
    """Hook into Blinker signal_order to trace emissions."""
    try:
        from core.data_bridge import signal_order

        def on_order_signal(sender, **kwargs):
            """Trace when Blinker emits signal_order."""
            payload = sender if isinstance(sender, dict) else kwargs
            symbol = payload.get("Symbol", "N/A")
            status = payload.get("OrderStatus", "?")
            logger.trace(f"DTC->Blinker emitted (Symbol={symbol}, Status={status})")

        # Connect with weak=False to prevent garbage collection
        signal_order.connect(on_order_signal, weak=False)
        logger.trace("Hooked: signal_order (Blinker)")
        return True

    except Exception as e:
        logger.error(f"Failed to hook signal_order: {e}", exc=e)
        return False


def _patch_qt_marshal() -> bool:
    """Monkey-patch marshal_to_qt_thread to trace Qt thread dispatching."""
    try:
        from utils import qt_bridge

        # Save original function
        original_marshal = qt_bridge.marshal_to_qt_thread

        @functools.wraps(original_marshal)
        def traced_marshal(func: Callable, *args, **kwargs) -> Any:
            """Traced version of marshal_to_qt_thread."""
            func_name = getattr(func, "__name__", str(func))

            try:
                logger.trace(f"Router->Qt marshaling ({func_name})")
                result = original_marshal(func, *args, **kwargs)
                logger.trace(f"Qt->Marshaled OK ({func_name})")
                return result
            except Exception as e:
                logger.error(f"Qt marshal FAILED ({func_name}): {e}", exc=e)
                raise

        # Replace with traced version in qt_bridge module
        qt_bridge.marshal_to_qt_thread = traced_marshal

        # ALSO patch MessageRouter's local reference (imported via "from utils.qt_bridge import")
        try:
            from core import message_router
            message_router.marshal_to_qt_thread = traced_marshal
            logger.trace("Patched: marshal_to_qt_thread (module + MessageRouter)")
        except Exception as e:
            logger.trace(f"Patched: marshal_to_qt_thread (module only, MessageRouter patch failed: {e})")

        return True

    except Exception as e:
        logger.error(f"Failed to patch marshal_to_qt_thread: {e}", exc=e)
        return False


def _patch_message_router() -> bool:
    """Patch MessageRouter to trace order signal handler."""
    try:
        from core.message_router import MessageRouter

        # Save original method
        original_on_order_signal = MessageRouter._on_order_signal

        @functools.wraps(original_on_order_signal)
        def traced_on_order_signal(self, sender, **kwargs):
            """Traced version of MessageRouter._on_order_signal."""
            msg = sender if isinstance(sender, dict) else kwargs
            symbol = msg.get("Symbol", "N/A")
            status = msg.get("OrderStatus", "?")

            logger.trace(f"Router->MessageRouter._on_order_signal (Symbol={symbol}, Status={status})")

            try:
                result = original_on_order_signal(self, sender, **kwargs)
                logger.trace(f"Router->Handler complete (Symbol={symbol})")
                return result
            except Exception as e:
                logger.error(f"Router handler FAILED (Symbol={symbol}): {e}", exc=e)
                raise

        # Replace with traced version
        MessageRouter._on_order_signal = traced_on_order_signal
        logger.trace("Patched: MessageRouter._on_order_signal")
        return True

    except Exception as e:
        logger.error(f"Failed to patch MessageRouter: {e}", exc=e)
        return False


def _patch_panel2() -> bool:
    """Monkey-patch Panel2.on_order_update to trace order reception."""
    try:
        from panels.panel2 import Panel2

        # Save original method
        original_on_order_update = Panel2.on_order_update

        @functools.wraps(original_on_order_update)
        def traced_on_order_update(self, payload: dict) -> None:
            """Traced version of Panel2.on_order_update."""
            symbol = payload.get("Symbol", "N/A")
            status = payload.get("OrderStatus", "?")

            try:
                logger.trace(f"Qt->Panel2 received (Symbol={symbol}, Status={status})")
                result = original_on_order_update(self, payload)
                logger.trace(f"Panel2->Processed OK (Symbol={symbol})")
                return result
            except Exception as e:
                logger.error(f"Panel2 processing FAILED (Symbol={symbol}): {e}", exc=e)
                # Don't re-raise - allow app to continue

        # Replace with traced version
        Panel2.on_order_update = traced_on_order_update
        logger.trace("Patched: Panel2.on_order_update")
        return True

    except Exception as e:
        logger.error(f"Failed to patch Panel2.on_order_update: {e}", exc=e)
        return False


# ==================== Main Entry Point ====================
def main():
    """Standalone entry point for testing."""
    print("="*80)
    print("Order Signal Tracer - Standalone Test Mode")
    print("="*80)
    print()

    attach_order_trace()

    print()
    print("Tracer attached successfully!")
    print(f"Log file: {LOG_FILE}")
    print()
    print("To use in your app, add to main.py:")
    print("    if os.getenv('DEBUG_DTC', '1') == '1':")
    print("        from tools.signal_trace_orders import attach_order_trace")
    print("        attach_order_trace()")


if __name__ == "__main__":
    main()
