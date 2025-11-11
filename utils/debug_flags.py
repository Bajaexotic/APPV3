"""
Debug Flags and Throttling Infrastructure

Purpose:
    Centralized management of debug flags and output throttling to avoid
    console spam during development and testing.

Background:
    Debug logging was scattered across multiple files with inconsistent patterns:
    - data_bridge.py: DEBUG_DATA, DEBUG_DTC flags with manual throttling
    - app_manager.py: Inline debug prints
    - Various tools: Ad-hoc debug toggles

    This module consolidates all debug infrastructure into one place.

Usage:
    from utils.debug_flags import get_debug_flags, should_log_debug, throttle

    # Check if debug mode is enabled
    flags = get_debug_flags()
    if flags.data:
        print("Debug data enabled")

    # Throttled logging (prevents spam)
    if should_log_debug("balance_update", interval_ms=2000):
        print(f"Balance update: {balance}")

    # Use as context manager
    with throttle("position_update", interval_ms=1000) as allowed:
        if allowed:
            print(f"Position: {position}")
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Dict, Optional


@dataclass
class DebugFlags:
    """
    Centralized debug flag configuration.

    Attributes:
        data: Enable DEBUG_DATA logging (general data flow)
        dtc: Enable DEBUG_DTC logging (DTC protocol details)
        signals: Enable signal routing/emission logging
        audit: Enable signal audit at startup
        theme: Enable theme switching logging
        all: Enable all debug flags

    Usage:
        flags = get_debug_flags()
        if flags.data:
            print("Data debug enabled")
    """

    data: bool = False
    dtc: bool = False
    signals: bool = False
    audit: bool = False
    theme: bool = False
    all: bool = False

    def __post_init__(self):
        """If 'all' is True, enable all flags."""
        if self.all:
            self.data = True
            self.dtc = True
            self.signals = True
            self.audit = True
            self.theme = True


# Global cache for debug flags
_DEBUG_FLAGS: Optional[DebugFlags] = None


def get_debug_flags() -> DebugFlags:
    """
    Get debug flags from config.settings.

    Caches result to avoid repeated imports.

    Returns:
        DebugFlags instance with all flags set

    Example:
        flags = get_debug_flags()
        if flags.data:
            print("DEBUG_DATA is enabled")
    """
    global _DEBUG_FLAGS

    if _DEBUG_FLAGS is None:
        try:
            from config.settings import DEBUG_DATA, DEBUG_DTC
        except Exception:
            DEBUG_DATA = False
            DEBUG_DTC = False

        # Check environment variables
        import os

        debug_signals = os.getenv("DEBUG_SIGNALS", "0") == "1"
        debug_audit = os.getenv("DEBUG_SIGNAL_AUDIT", "0") == "1"
        debug_theme = os.getenv("DEBUG_THEME", "0") == "1"
        debug_all = os.getenv("DEBUG_ALL", "0") == "1"

        _DEBUG_FLAGS = DebugFlags(
            data=DEBUG_DATA,
            dtc=DEBUG_DTC,
            signals=debug_signals,
            audit=debug_audit,
            theme=debug_theme,
            all=debug_all,
        )

    return _DEBUG_FLAGS


def is_debug_enabled(flag: str) -> bool:
    """
    Check if a specific debug flag is enabled.

    Args:
        flag: One of "data", "dtc", "signals", "audit", "theme", "all"

    Returns:
        True if flag is enabled, False otherwise

    Example:
        if is_debug_enabled("data"):
            print("Data debug is on")
    """
    flags = get_debug_flags()
    return getattr(flags, flag.lower(), False)


# -------------------- Throttling --------------------


class DebugThrottler:
    """
    Throttle debug output to prevent console spam.

    Maintains a per-key timestamp map to limit output frequency.

    Usage:
        throttler = DebugThrottler()

        # Allow at most one message every 2 seconds
        if throttler.should_log("balance", interval_ms=2000):
            print("Balance update")

        # Or use as context manager
        with throttler.throttle("position", interval_ms=1000) as allowed:
            if allowed:
                print("Position update")
    """

    def __init__(self):
        """Initialize throttler with empty state."""
        self._last_log_time: dict[str, float] = {}

    def should_log(self, key: str, interval_ms: int = 1000) -> bool:
        """
        Check if logging is allowed for the given key.

        Args:
            key: Unique identifier for this log type
            interval_ms: Minimum milliseconds between logs

        Returns:
            True if logging is allowed, False if throttled

        Example:
            if throttler.should_log("order_update", interval_ms=500):
                print(f"Order: {order}")
        """
        now_ms = time.monotonic() * 1000.0
        last_time = self._last_log_time.get(key, 0.0)

        if now_ms >= last_time + interval_ms:
            self._last_log_time[key] = now_ms
            return True

        return False

    def throttle(self, key: str, interval_ms: int = 1000):
        """
        Context manager for throttled logging.

        Args:
            key: Unique identifier for this log type
            interval_ms: Minimum milliseconds between logs

        Returns:
            Context manager yielding True/False

        Example:
            with throttler.throttle("balance", 2000) as allowed:
                if allowed:
                    print("Balance update")
        """

        class ThrottleContext:
            def __init__(self, throttler: DebugThrottler, key: str, interval_ms: int):
                self.throttler = throttler
                self.key = key
                self.interval_ms = interval_ms
                self.allowed = False

            def __enter__(self):
                self.allowed = self.throttler.should_log(self.key, self.interval_ms)
                return self.allowed

            def __exit__(self, *args):
                pass

        return ThrottleContext(self, key, interval_ms)


# Global throttler instance
_THROTTLER = DebugThrottler()


def should_log_debug(key: str, interval_ms: int = 1000) -> bool:
    """
    Convenience function for throttled debug logging.

    Args:
        key: Unique identifier for this log type
        interval_ms: Minimum milliseconds between logs

    Returns:
        True if logging is allowed, False if throttled

    Example:
        if should_log_debug("balance_update", interval_ms=2000):
            print(f"Balance: {balance}")

    Notes:
        - Uses global throttler instance
        - Safe to call from any thread
        - Key should be unique per log site
    """
    return _THROTTLER.should_log(key, interval_ms)


def throttle(key: str, interval_ms: int = 1000):
    """
    Context manager for throttled debug logging.

    Args:
        key: Unique identifier for this log type
        interval_ms: Minimum milliseconds between logs

    Returns:
        Context manager yielding True/False

    Example:
        with throttle("position_update", 1000) as allowed:
            if allowed:
                print(f"Position: {position}")

    Notes:
        - Uses global throttler instance
        - Safe to call from any thread
    """
    return _THROTTLER.throttle(key, interval_ms)


# -------------------- Debug helpers --------------------


def debug_print(category: str, message: str, throttle_ms: Optional[int] = None) -> None:
    """
    Print debug message if category is enabled.

    Args:
        category: Debug category ("data", "dtc", "signals", etc.)
        message: Message to print
        throttle_ms: Optional throttle interval in milliseconds

    Example:
        debug_print("data", "Balance update received", throttle_ms=2000)

    Notes:
        - Automatically checks if category is enabled
        - Applies throttling if specified
        - No-op if debug flag is off
    """
    if not is_debug_enabled(category):
        return

    # Generate throttle key from category and first 20 chars of message
    throttle_key = f"{category}:{message[:20]}"

    if throttle_ms is not None:
        if should_log_debug(throttle_key, interval_ms=throttle_ms):
            print(f"[DEBUG:{category.upper()}] {message}")
    else:
        print(f"[DEBUG:{category.upper()}] {message}")


def debug_data(message: str, throttle_ms: Optional[int] = None) -> None:
    """Shortcut for debug_print("data", ...)"""
    debug_print("data", message, throttle_ms)


def debug_dtc(message: str, throttle_ms: Optional[int] = None) -> None:
    """Shortcut for debug_print("dtc", ...)"""
    debug_print("dtc", message, throttle_ms)


def debug_signal(message: str, throttle_ms: Optional[int] = None) -> None:
    """Shortcut for debug_print("signals", ...)"""
    debug_print("signals", message, throttle_ms)


# -------------------- Configuration --------------------


def configure_debug_flags(
    data: Optional[bool] = None,
    dtc: Optional[bool] = None,
    signals: Optional[bool] = None,
    audit: Optional[bool] = None,
    theme: Optional[bool] = None,
    all: Optional[bool] = None,
) -> None:
    """
    Manually configure debug flags (overrides config.settings).

    Args:
        data: Enable DEBUG_DATA
        dtc: Enable DEBUG_DTC
        signals: Enable DEBUG_SIGNALS
        audit: Enable DEBUG_SIGNAL_AUDIT
        theme: Enable DEBUG_THEME
        all: Enable all flags

    Example:
        # Enable all debug flags
        configure_debug_flags(all=True)

        # Enable only data and DTC logging
        configure_debug_flags(data=True, dtc=True)

    Notes:
        - Only updates flags that are explicitly passed
        - Useful for testing or runtime toggling
    """
    global _DEBUG_FLAGS

    if _DEBUG_FLAGS is None:
        _DEBUG_FLAGS = get_debug_flags()

    if data is not None:
        _DEBUG_FLAGS.data = data
    if dtc is not None:
        _DEBUG_FLAGS.dtc = dtc
    if signals is not None:
        _DEBUG_FLAGS.signals = signals
    if audit is not None:
        _DEBUG_FLAGS.audit = audit
    if theme is not None:
        _DEBUG_FLAGS.theme = theme
    if all is not None:
        _DEBUG_FLAGS.all = all
        if all:
            _DEBUG_FLAGS.data = True
            _DEBUG_FLAGS.dtc = True
            _DEBUG_FLAGS.signals = True
            _DEBUG_FLAGS.audit = True
            _DEBUG_FLAGS.theme = True


# -------------------- Testing utilities --------------------


def _test_throttling():
    """Test function for development - verifies throttling works."""
    print("Throttling Test")
    print("=" * 50)

    # Test 1: Rapid calls with 1-second throttle
    print("\nTest 1: Rapid calls (1s throttle)")
    for i in range(5):
        if should_log_debug("test1", interval_ms=1000):
            print(f"  Message {i} logged")
        else:
            print(f"  Message {i} throttled")
        time.sleep(0.3)  # 300ms between calls

    # Test 2: Context manager
    print("\nTest 2: Context manager (500ms throttle)")
    for i in range(5):
        with throttle("test2", interval_ms=500) as allowed:
            if allowed:
                print(f"  Message {i} logged")
            else:
                print(f"  Message {i} throttled")
        time.sleep(0.2)  # 200ms between calls

    # Test 3: Helper functions
    print("\nTest 3: Helper functions")
    configure_debug_flags(data=True, dtc=True)
    debug_data("Data message 1")
    debug_data("Data message 2", throttle_ms=1000)
    time.sleep(0.5)
    debug_data("Data message 3", throttle_ms=1000)  # Should be throttled
    time.sleep(0.6)
    debug_data("Data message 4", throttle_ms=1000)  # Should log


if __name__ == "__main__":
    _test_throttling()
