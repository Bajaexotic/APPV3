"""
APPSIERRA Live-Data Propagation Trace Hooks
Instrument code to trace DTC messages through the entire pipeline
"""

import functools


# Global trace log
trace_log = []


def trace_hook(component: str, function: str, event: str):
    """Decorator to trace function calls and events"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg_type = kwargs.get("type") or (args[0].get("Type") if args and isinstance(args[0], dict) else "unknown")
            trace_entry = f"[{component}] {function}::{event} | msg_type={msg_type}"
            trace_log.append(trace_entry)
            print(f"TRACE: {trace_entry}")
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                trace_log.append(f"  ERROR in {function}: {e!s}")
                raise

        return wrapper

    return decorator


# ============================================================================
# TRACE POINTS TO INSERT
# ============================================================================

trace_points = [
    {
        "file": "core/data_bridge.py",
        "function": "_on_ready_read",
        "insert_at": "beginning",
        "code": 'print("TRACE: data_bridge._on_ready_read() START")',
    },
    {
        "file": "core/data_bridge.py",
        "function": "_handle_frame",
        "insert_at": "after_decode",
        "code": 'print(f"TRACE: data_bridge._handle_frame decoded type={dtc.get("Type")}")',
    },
    {
        "file": "core/data_bridge.py",
        "function": "_dtc_to_app_event",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: _dtc_to_app_event() type={dtc.get("Type")}")',
    },
    {
        "file": "core/data_bridge.py",
        "function": "_emit_app",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: _emit_app() type={app_msg.type} | Emitting signals...")',
    },
    {
        "file": "core/message_router.py",
        "function": "route",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: message_router.route() type={msg.get("type")}")',
    },
    {
        "file": "core/state_manager.py",
        "function": "update_balance",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: state_manager.update_balance({balance})")',
    },
    {
        "file": "core/app_manager.py",
        "function": "_on_balance",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: app_manager._on_balance() received signal")',
    },
    {
        "file": "panels/panel1.py",
        "function": "set_account_balance",
        "insert_at": "beginning",
        "code": 'print(f"TRACE: panel1.set_account_balance({balance})")',
    },
]

print("=" * 100)
print("PROPAGATION TRACE POINTS IDENTIFIED")
print("=" * 100)
for i, point in enumerate(trace_points, 1):
    print(f"\n[{i}] {point['file']}::{point['function']}")
    print(f"    Insert: {point['insert_at']}")
    print(f"    Code: {point['code']}")
