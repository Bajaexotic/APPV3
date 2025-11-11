"""
Qt Thread Safety Bridge

Purpose:
    Centralized utilities for safely marshaling operations from background threads
    to the main Qt event loop thread.

Background:
    Blinker signals execute in the sender's thread (which may be a background thread
    for DTC socket operations). Any code that touches Qt widgets MUST run on the main
    thread, or Qt will crash with "QObject: Cannot create children for a parent that
    is in a different thread."

Solution:
    This module provides helpers to safely marshal callbacks to the Qt thread using
    QTimer.singleShot(0, ...), which posts the callback to the event loop.

Usage:
    # From background thread (e.g., Blinker signal handler):
    from utils.qt_bridge import marshal_to_qt_thread

    def on_balance_update(balance_data):
        # This might be called from DTC socket thread
        marshal_to_qt_thread(update_ui, balance_data)

    def update_ui(balance_data):
        # This will ALWAYS run on Qt main thread
        panel.set_balance(balance_data["balance"])
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6 import QtCore


def marshal_to_qt_thread(callback: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Execute callback in the main Qt thread.

    Safely posts the callback to the Qt event loop, ensuring it executes
    on the main thread regardless of the caller's thread.

    Args:
        callback: The function to call on the main thread
        *args: Positional arguments to pass to callback
        **kwargs: Keyword arguments to pass to callback

    Example:
        # From any thread:
        marshal_to_qt_thread(panel.set_balance, 50000.0)

        # With multiple args:
        marshal_to_qt_thread(panel.update_position, symbol="ES", qty=2, avg=5000.0)

    Notes:
        - Uses QTimer.singleShot(0, ...) which posts to event loop
        - Callback executes on next event loop iteration
        - Non-blocking for caller
        - Safe to call from any thread, including main thread
    """
    try:
        QtCore.QTimer.singleShot(0, lambda: callback(*args, **kwargs))
    except Exception as e:
        # Log but don't crash if marshaling fails
        import sys

        print(f"ERROR: Qt thread marshaling failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()


def is_main_thread() -> bool:
    """
    Check if currently executing on the Qt main thread.

    Returns:
        True if on main thread, False otherwise

    Example:
        if not is_main_thread():
            marshal_to_qt_thread(update_ui, data)
        else:
            update_ui(data)
    """
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return False
        return QtCore.QThread.currentThread() == app.thread()
    except Exception:
        # If we can't determine, assume we're NOT on main thread (safer)
        return False


def marshal_if_needed(callback: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Execute callback on main thread only if not already on main thread.

    Optimized version of marshal_to_qt_thread that skips marshaling
    if already on the main thread.

    Args:
        callback: The function to call
        *args: Positional arguments to pass to callback
        **kwargs: Keyword arguments to pass to callback

    Example:
        # Automatically marshals only if needed:
        marshal_if_needed(panel.set_balance, 50000.0)

    Notes:
        - Use this when you're unsure which thread you're on
        - Slightly more overhead than direct marshal_to_qt_thread
        - Avoids unnecessary event loop posting if already on main thread
    """
    if is_main_thread():
        try:
            callback(*args, **kwargs)
        except Exception as e:
            import sys

            print(f"ERROR: Direct callback failed: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
    else:
        marshal_to_qt_thread(callback, *args, **kwargs)


class QtThreadSafeMixin:
    """
    Mixin class to make method calls thread-safe automatically.

    Usage:
        class MyPanel(QtWidgets.QWidget, QtThreadSafeMixin):
            @qt_safe
            def set_balance(self, balance: float):
                # This method will always run on main thread
                self.balance_label.setText(f"${balance:,.2f}")

    Notes:
        - Apply @qt_safe decorator to methods that touch Qt widgets
        - Methods will automatically marshal to main thread if needed
    """

    pass


def qt_safe(method: Callable) -> Callable:
    """
    Decorator to make a method thread-safe for Qt operations.

    Automatically marshals the method call to the Qt main thread
    if it's called from a background thread.

    Args:
        method: The method to decorate

    Returns:
        Wrapped method that's thread-safe

    Example:
        class Panel1(QtWidgets.QWidget):
            @qt_safe
            def set_balance(self, balance: float):
                # Always safe to touch Qt widgets here
                self.balance_label.setText(f"${balance:,.2f}")

        # Can call from any thread:
        panel.set_balance(50000.0)  # Automatically marshaled if needed

    Notes:
        - Adds minimal overhead (thread check)
        - Safe to apply to methods already on main thread
        - Use for any method that touches Qt widgets
    """

    def wrapper(self, *args: Any, **kwargs: Any):
        if is_main_thread():
            return method(self, *args, **kwargs)
        else:
            marshal_to_qt_thread(method, self, *args, **kwargs)
            return None  # Async call, no return value

    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


# -------------------- Testing utilities --------------------


def _test_marshal():
    """Test function for development - verifies marshaling works."""
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    print(f"Main thread: {app.thread()}")
    print(f"Current thread: {QtCore.QThread.currentThread()}")
    print(f"Is main thread: {is_main_thread()}")

    def callback(msg: str):
        print(f"Callback executed: {msg}")
        print(f"  Thread: {QtCore.QThread.currentThread()}")
        print(f"  Is main: {is_main_thread()}")

    # Test direct call
    print("\nTest 1: Direct call")
    callback("direct")

    # Test marshal
    print("\nTest 2: Marshaled call")
    marshal_to_qt_thread(callback, "marshaled")

    # Process events to execute queued callback
    app.processEvents()

    print("\nTest complete")


if __name__ == "__main__":
    _test_marshal()
