"""
DTC Protocol Core - Shared message framing and utilities

This module provides low-level DTC protocol utilities that work with both
Qt-based and raw socket implementations. Eliminates duplication across:
- core/data_bridge.py (Qt production client)
- services/dtc_json_client.py (threading client)
- tools/dtc_probe.py (diagnostic client)
- tools/dtc_test_framework.py (test utilities)

Functions:
- Message framing: frame_message(), parse_messages()
- Logon helpers: build_logon_request(), build_heartbeat()
- Request builders: build_account_balance_request(), etc.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from services.dtc_constants import (
    ACCOUNT_BALANCE_REQUEST,
    CURRENT_POSITIONS_REQUEST,
    HEARTBEAT,
    HISTORICAL_ORDER_FILLS_REQUEST,
    LOGON_REQUEST,
    LOGON_RESPONSE,
    NULL_TERMINATOR,
    OPEN_ORDERS_REQUEST,
    TRADE_ACCOUNTS_REQUEST,
    TRADE_MODE_DEMO,
    TRADE_MODE_LIVE,
    TRADE_MODE_SIMULATED,
)


# ============================================================================
# Message Framing
# ============================================================================


def frame_message(msg: dict) -> bytes:
    """
    Frame a DTC message for transmission (JSON + null terminator).

    Args:
        msg: Message dictionary (must include 'Type' field)

    Returns:
        Framed message as bytes ready for socket transmission

    Example:
        >>> frame_message({"Type": 1, "ProtocolVersion": 8})
        b'{"Type":1,"ProtocolVersion":8}\x00'
    """
    return json.dumps(msg).encode("utf-8") + NULL_TERMINATOR


def parse_messages(buffer: bytearray) -> tuple[list[dict], bytearray]:
    """
    Parse null-terminated JSON messages from a byte buffer.

    Args:
        buffer: Byte buffer containing zero or more complete messages

    Returns:
        Tuple of (parsed messages list, remaining buffer)

    Example:
        >>> buf = bytearray(b'{"Type":2}\x00{"Type":3}\x00partial')
        >>> messages, remaining = parse_messages(buf)
        >>> len(messages)
        2
        >>> remaining
        bytearray(b'partial')
    """
    messages = []

    while NULL_TERMINATOR in buffer:
        # Find null terminator
        idx = buffer.index(NULL_TERMINATOR)
        msg_bytes = bytes(buffer[:idx])
        buffer = buffer[idx + 1 :]  # Skip the null terminator

        # Parse JSON
        if msg_bytes:
            try:
                msg = json.loads(msg_bytes.decode("utf-8"))
                messages.append(msg)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Invalid message - skip it
                pass

    return messages, buffer


# ============================================================================
# Logon & Authentication
# ============================================================================


def build_logon_request(
    protocol_version: int = 8,
    client_name: str = "APPSIERRA",
    heartbeat_interval: int = 5,
    username: str = "",
    password: str = "",
    trade_mode: int = TRADE_MODE_LIVE,
    **extra_fields,
) -> dict:
    """
    Build a DTC LOGON_REQUEST message.

    Args:
        protocol_version: DTC protocol version (default 8)
        client_name: Client identification string
        heartbeat_interval: Heartbeat interval in seconds
        username: Optional authentication username
        password: Optional authentication password
        trade_mode: Trading mode (LIVE, DEMO, or SIMULATED)
        **extra_fields: Additional message fields

    Returns:
        LOGON_REQUEST message dictionary

    Example:
        >>> msg = build_logon_request(username="trader1", password="secret")
        >>> msg["Type"]
        1
    """
    msg = {
        "Type": LOGON_REQUEST,
        "ProtocolVersion": protocol_version,
        "ClientName": client_name,
        "HeartbeatIntervalInSeconds": heartbeat_interval,
        "Username": username,
        "Password": password,
        "TradeMode": trade_mode,
    }

    # Add any extra fields
    msg.update(extra_fields)

    return msg


def is_logon_success(logon_response: dict) -> bool:
    """
    Check if a LOGON_RESPONSE indicates successful logon.

    Args:
        logon_response: LOGON_RESPONSE message dictionary

    Returns:
        True if logon was successful

    Example:
        >>> is_logon_success({"Type": 2, "Result": "LOGON_SUCCESS"})
        True
        >>> is_logon_success({"Type": 2, "Result": "FAILED"})
        False
    """
    if logon_response.get("Type") != LOGON_RESPONSE:
        return False

    result = logon_response.get("Result", logon_response.get("Status", ""))

    # Check for success indicators
    success_tokens = {"LOGON_SUCCESS", "SUCCESS", "OK", "0", "1", 0, 1, True}

    return result in success_tokens or (isinstance(result, str) and result.upper() in success_tokens)


# ============================================================================
# Heartbeat
# ============================================================================


def build_heartbeat() -> dict:
    """
    Build a DTC HEARTBEAT message.

    Returns:
        HEARTBEAT message dictionary

    Example:
        >>> msg = build_heartbeat()
        >>> msg
        {'Type': 3}
    """
    return {"Type": HEARTBEAT}


# ============================================================================
# Account & Position Requests
# ============================================================================


def build_trade_accounts_request(request_id: int = 1) -> dict:
    """
    Build a TRADE_ACCOUNTS_REQUEST message.

    Args:
        request_id: Request identifier

    Returns:
        TRADE_ACCOUNTS_REQUEST message dictionary
    """
    return {
        "Type": TRADE_ACCOUNTS_REQUEST,
        "RequestID": request_id,
    }


def build_account_balance_request(
    trade_account: str,
    request_id: int = 1,
) -> dict:
    """
    Build an ACCOUNT_BALANCE_REQUEST message.

    Args:
        trade_account: Trading account identifier
        request_id: Request identifier

    Returns:
        ACCOUNT_BALANCE_REQUEST message dictionary
    """
    return {
        "Type": ACCOUNT_BALANCE_REQUEST,
        "RequestID": request_id,
        "TradeAccount": trade_account,
    }


def build_positions_request(
    trade_account: str,
    request_id: int = 1,
) -> dict:
    """
    Build a CURRENT_POSITIONS_REQUEST message.

    Args:
        trade_account: Trading account identifier
        request_id: Request identifier

    Returns:
        CURRENT_POSITIONS_REQUEST message dictionary
    """
    return {
        "Type": CURRENT_POSITIONS_REQUEST,
        "RequestID": request_id,
        "TradeAccount": trade_account,
    }


def build_open_orders_request(
    trade_account: str,
    request_id: int = 1,
) -> dict:
    """
    Build an OPEN_ORDERS_REQUEST message.

    Args:
        trade_account: Trading account identifier
        request_id: Request identifier

    Returns:
        OPEN_ORDERS_REQUEST message dictionary
    """
    return {
        "Type": OPEN_ORDERS_REQUEST,
        "RequestID": request_id,
        "TradeAccount": trade_account,
    }


def build_historical_order_fills_request(
    trade_account: str,
    request_id: int = 1,
    number_of_days: Optional[int] = None,
) -> dict:
    """
    Build a HISTORICAL_ORDER_FILLS_REQUEST message.

    Args:
        trade_account: Trading account identifier
        request_id: Request identifier
        number_of_days: Optional number of days to retrieve

    Returns:
        HISTORICAL_ORDER_FILLS_REQUEST message dictionary
    """
    msg = {
        "Type": HISTORICAL_ORDER_FILLS_REQUEST,
        "RequestID": request_id,
        "TradeAccount": trade_account,
    }

    if number_of_days is not None:
        msg["NumberOfDays"] = number_of_days

    return msg


# ============================================================================
# Message Validation
# ============================================================================


def validate_message(msg: dict) -> bool:
    """
    Validate that a message dictionary is well-formed.

    Args:
        msg: Message dictionary to validate

    Returns:
        True if message is valid, False otherwise

    Example:
        >>> validate_message({"Type": 1, "ProtocolVersion": 8})
        True
        >>> validate_message({"NoType": "value"})
        False
    """
    # Must be a dict
    if not isinstance(msg, dict):
        return False

    # Must have 'Type' field
    if "Type" not in msg:
        return False

    # Type must be int or str
    msg_type = msg["Type"]
    if not isinstance(msg_type, (int, str)):
        return False

    return True


# ============================================================================
# Trade Mode Helpers
# ============================================================================


def get_trade_mode_name(mode: int) -> str:
    """
    Convert trade mode constant to human-readable name.

    Args:
        mode: Trade mode constant

    Returns:
        Mode name string

    Example:
        >>> get_trade_mode_name(TRADE_MODE_LIVE)
        'LIVE'
    """
    modes = {
        TRADE_MODE_DEMO: "DEMO",
        TRADE_MODE_LIVE: "LIVE",
        TRADE_MODE_SIMULATED: "SIMULATED",
    }

    return modes.get(mode, f"UNKNOWN_{mode}")


def parse_trade_mode(mode_str: str) -> int:
    """
    Parse trade mode string to constant.

    Args:
        mode_str: Mode string ('LIVE', 'DEMO', 'SIM', etc.)

    Returns:
        Trade mode constant (defaults to LIVE if unknown)

    Example:
        >>> parse_trade_mode("LIVE")
        1
        >>> parse_trade_mode("SIM")
        2
    """
    mode_upper = mode_str.upper()

    if mode_upper in ("LIVE", "PROD", "PRODUCTION"):
        return TRADE_MODE_LIVE
    elif mode_upper in ("DEMO", "PAPER"):
        return TRADE_MODE_DEMO
    elif mode_upper in ("SIM", "SIMULATED", "SIMULATION"):
        return TRADE_MODE_SIMULATED
    else:
        return TRADE_MODE_LIVE  # Safe default


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    """
    Example demonstrating DTC protocol utilities.
    """
    print("DTC Protocol Utilities Example\n")

    # Build and frame a logon request
    logon = build_logon_request(
        username="trader",
        password="secret",
        trade_mode=TRADE_MODE_LIVE,
    )
    print(f"Logon message: {logon}")

    framed = frame_message(logon)
    print(f"Framed ({len(framed)} bytes): {framed[:50]}...")

    # Build a heartbeat
    hb = build_heartbeat()
    print(f"\nHeartbeat: {hb}")

    # Build account requests
    balance_req = build_account_balance_request("120005")
    print(f"\nBalance request: {balance_req}")

    positions_req = build_positions_request("120005")
    print(f"Positions request: {positions_req}")

    # Parse messages from buffer
    print("\nParsing messages from buffer:")
    buffer = bytearray(
        b'{"Type":2,"Result":"LOGON_SUCCESS"}\x00'
        b'{"Type":3}\x00'
        b'{"Type":600,"CashBalance":50000}\x00'
        b"incomplete"
    )

    messages, remaining = parse_messages(buffer)
    print(f"Parsed {len(messages)} messages:")
    for msg in messages:
        print(f"  {msg}")
    print(f"Remaining buffer: {remaining}")

    # Validate logon response
    logon_response = {"Type": 2, "Result": "LOGON_SUCCESS"}
    print(f"\nLogon success? {is_logon_success(logon_response)}")

    print("\n✓ All examples completed successfully")
