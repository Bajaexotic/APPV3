"""
Trade Mode Detection and Management

Purpose:
    Centralized logic for detecting and managing trading modes (LIVE, SIM, DEBUG)
    based on DTC account information from orders and positions.

Background:
    The app can operate in multiple modes:
    - LIVE: Real money trading (account matches LIVE_ACCOUNT config)
    - SIM: Paper trading (account starts with "Sim")
    - DEBUG: Development/testing mode

    Previously, mode detection logic was duplicated in:
    - app_manager.py:232-242 (_on_order)
    - app_manager.py:275-287 (_on_position)

    This module consolidates that logic into reusable functions.

Usage:
    from utils.trade_mode import detect_mode_from_account, should_switch_mode

    # Detect mode from DTC message
    account = msg.get("TradeAccount", "")
    new_mode = detect_mode_from_account(account)

    # Check if mode switch is warranted
    if should_switch_mode(account, qty=2):
        panel.set_trading_mode(new_mode)
"""

from __future__ import annotations

import time
from collections import deque
from typing import Literal, Optional


# Import settings lazily to avoid circular imports
_LIVE_ACCOUNT: Optional[str] = None

# Debounce configuration
DEBOUNCE_WINDOW_MS = 750  # 750ms window
REQUIRED_CONSECUTIVE = 2  # Require 2 consecutive agreeing signals

# Mode candidate queue: deque of (timestamp_ms, mode, account) tuples
_mode_candidates: deque[tuple[float, str, str]] = deque(maxlen=10)


def _get_live_account() -> str:
    """Lazy-load LIVE_ACCOUNT from config.settings."""
    global _LIVE_ACCOUNT
    if _LIVE_ACCOUNT is None:
        try:
            from config.settings import LIVE_ACCOUNT

            _LIVE_ACCOUNT = LIVE_ACCOUNT or ""
        except Exception:
            _LIVE_ACCOUNT = ""
    return _LIVE_ACCOUNT


def detect_mode_from_account(account: str) -> Literal["LIVE", "SIM", "DEBUG"]:
    """
    Detect trading mode from DTC account identifier.

    Args:
        account: TradeAccount string from DTC message (e.g., "120005", "Sim1")

    Returns:
        One of: "LIVE", "SIM", or "DEBUG"

    Examples:
        detect_mode_from_account("120005")  # "LIVE" (if matches LIVE_ACCOUNT)
        detect_mode_from_account("Sim1")    # "SIM"
        detect_mode_from_account("")        # "DEBUG"

    Notes:
        - Empty/missing account defaults to DEBUG mode
        - Account matching LIVE_ACCOUNT config → LIVE mode
        - Account starting with "Sim" → SIM mode
        - Everything else → DEBUG mode
    """
    if not account or not isinstance(account, str):
        return "DEBUG"

    account = account.strip()
    if not account:
        return "DEBUG"

    live_account = _get_live_account()

    # Check for LIVE account match
    if live_account and account == live_account:
        return "LIVE"

    # Check for SIM account
    if account.startswith("Sim"):
        return "SIM"

    # Default to DEBUG for unknown accounts
    return "DEBUG"


def should_switch_mode(account: str, qty: Optional[int] = None, require_active_position: bool = True) -> bool:
    """
    Determine if mode switch should occur based on DTC message.

    Args:
        account: TradeAccount string from DTC message
        qty: Position quantity (if from position update)
        require_active_position: If True, only switch on non-zero positions

    Returns:
        True if mode switch should occur, False otherwise

    Examples:
        # Order message (always switch):
        should_switch_mode("120005")  # True

        # Position message with active position:
        should_switch_mode("Sim1", qty=2)  # True

        # Position message with zero position (flat):
        should_switch_mode("Sim1", qty=0)  # False (if require_active_position=True)

    Notes:
        - Orders always trigger mode switch (qty not required)
        - Positions only trigger switch if qty != 0 (prevents flicker on flat)
        - Empty/invalid accounts don't trigger switch
    """
    if not account or not isinstance(account, str):
        return False

    account = account.strip()
    if not account:
        return False

    # For position updates, check quantity
    if qty is not None and require_active_position:
        # Only switch on active positions (non-zero qty)
        if qty == 0:
            return False

    return True


def should_switch_mode_debounced(account: str, current_mode: Optional[str] = None, qty: Optional[int] = None) -> bool:
    """
    Debounced mode switch check - requires 2 consecutive agreeing signals within 750ms window.

    Args:
        account: TradeAccount string from DTC message
        current_mode: Currently active mode (for comparison)
        qty: Position quantity (if from position update)

    Returns:
        True if mode switch should occur after debounce, False otherwise

    Example:
        if should_switch_mode_debounced("Sim1", current_mode="LIVE"):
            # Switch to SIM mode
            panel.set_trading_mode("SIM", "Sim1")

    Notes:
        - Prevents rapid mode flickering by requiring consecutive signals
        - 750ms window ensures signals are recent
        - First call after long gap won't trigger switch (need 2 consecutive)
    """
    # First check if basic switch criteria are met
    if not should_switch_mode(account, qty=qty):
        return False

    # Detect mode from account
    new_mode = detect_mode_from_account(account)

    # If mode hasn't changed, no switch needed
    if current_mode and new_mode == current_mode:
        return False

    # Add candidate to queue
    now_ms = time.time() * 1000
    _mode_candidates.append((now_ms, new_mode, account))

    # Prune old candidates outside debounce window
    cutoff_ms = now_ms - DEBOUNCE_WINDOW_MS
    while _mode_candidates and _mode_candidates[0][0] < cutoff_ms:
        _mode_candidates.popleft()

    # Check if last N candidates agree
    if len(_mode_candidates) >= REQUIRED_CONSECUTIVE:
        recent_candidates = list(_mode_candidates)[-REQUIRED_CONSECUTIVE:]
        # All must agree on mode AND account
        if all(c[1] == new_mode and c[2] == account for c in recent_candidates):
            # Clear queue after successful debounce
            _mode_candidates.clear()
            return True

    return False


def reset_debounce() -> None:
    """
    Reset the debounce queue.
    Useful after explicit mode changes or on disconnect.
    """
    _mode_candidates.clear()


def get_mode_display_name(mode: str) -> str:
    """
    Get human-readable display name for mode.

    Args:
        mode: One of "LIVE", "SIM", "DEBUG"

    Returns:
        Display name for UI

    Examples:
        get_mode_display_name("LIVE")   # "Live Trading"
        get_mode_display_name("SIM")    # "Paper Trading"
        get_mode_display_name("DEBUG")  # "Debug Mode"
    """
    mode_names = {
        "LIVE": "Live Trading",
        "SIM": "Paper Trading",
        "DEBUG": "Debug Mode",
    }
    return mode_names.get(mode.upper(), mode)


def is_live_mode(mode: str) -> bool:
    """Check if mode is LIVE."""
    return mode.upper() == "LIVE"


def is_sim_mode(mode: str) -> bool:
    """Check if mode is SIM."""
    return mode.upper() == "SIM"


def is_debug_mode(mode: str) -> bool:
    """Check if mode is DEBUG."""
    return mode.upper() == "DEBUG"


# -------------------- Auto-detection from DTC messages --------------------


def auto_detect_mode_from_order(order_msg: dict) -> Optional[str]:
    """
    Auto-detect trading mode from DTC ORDER_UPDATE message.

    Args:
        order_msg: DTC order message dict

    Returns:
        Mode string ("LIVE" | "SIM" | "DEBUG") or None if no account

    Example:
        mode = auto_detect_mode_from_order(order_msg)
        if mode:
            panel.set_trading_mode(mode)

    Notes:
        - Extracts TradeAccount from message
        - Always returns mode (orders always trigger switch)
    """
    account = order_msg.get("TradeAccount", "")
    if not account:
        return None

    if should_switch_mode(account):
        return detect_mode_from_account(account)

    return None


def auto_detect_mode_from_position(position_msg: dict) -> Optional[str]:
    """
    Auto-detect trading mode from DTC POSITION_UPDATE message.

    Args:
        position_msg: DTC position message dict

    Returns:
        Mode string ("LIVE" | "SIM" | "DEBUG") or None if shouldn't switch

    Example:
        mode = auto_detect_mode_from_position(position_msg)
        if mode:
            panel.set_trading_mode(mode)

    Notes:
        - Extracts TradeAccount and qty from message
        - Only returns mode for active positions (qty != 0)
        - Returns None for flat positions to prevent flicker
    """
    account = position_msg.get("TradeAccount", "")
    qty = position_msg.get("qty", position_msg.get("PositionQuantity", 0))

    if not account:
        return None

    if should_switch_mode(account, qty=qty, require_active_position=True):
        return detect_mode_from_account(account)

    return None


# -------------------- Logging utilities --------------------


def log_mode_switch(old_mode: str, new_mode: str, account: str, logger=None) -> None:
    """
    Log a mode switch event.

    Args:
        old_mode: Previous mode
        new_mode: New mode
        account: Account that triggered the switch
        logger: Optional logger instance (uses print if None)

    Example:
        log_mode_switch("SIM", "LIVE", "120005", log)
    """
    msg = f"[AUTO-DETECT] Mode switch: {old_mode} → {new_mode} (account: {account})"

    if logger:
        try:
            logger.info(msg)
        except Exception:
            print(msg)
    else:
        print(msg)


# -------------------- Testing utilities --------------------


def _test_mode_detection():
    """Test function for development - verifies mode detection logic."""
    test_cases = [
        ("120005", None, "LIVE"),  # LIVE account
        ("Sim1", None, "SIM"),  # SIM account
        ("Sim2", None, "SIM"),  # Another SIM
        ("", None, "DEBUG"),  # Empty account
        ("Unknown123", None, "DEBUG"),  # Unknown account
    ]

    print("Trade Mode Detection Tests")
    print("=" * 50)

    for account, qty, expected_mode in test_cases:
        detected = detect_mode_from_account(account)
        status = "✓" if detected == expected_mode else "✗"
        print(f"{status} Account: {account!r:15} → {detected:5} (expected {expected_mode})")

    print("\nMode Switch Decision Tests")
    print("=" * 50)

    switch_cases = [
        ("120005", None, True),  # Order - always switch
        ("Sim1", 2, True),  # Active position - switch
        ("Sim1", 0, False),  # Flat position - don't switch
        ("", 5, False),  # No account - don't switch
    ]

    for account, qty, expected in switch_cases:
        should_switch = should_switch_mode(account, qty)
        status = "✓" if should_switch == expected else "✗"
        qty_str = f"qty={qty}" if qty is not None else "order"
        print(f"{status} Account: {account!r:15} {qty_str:8} → {should_switch} (expected {expected})")


if __name__ == "__main__":
    _test_mode_detection()
