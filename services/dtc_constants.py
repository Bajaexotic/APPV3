"""
DTC Protocol Message Type Constants and Utilities

Centralized constants for the Data and Trading Communications (DTC) Protocol.
All DTC clients and tools should import from this module to ensure consistency.

Spec: https://dtcprotocol.org/index.php?page=doc/DTCMessageDocumentation.php
"""

from typing import Union


# ============================================================================
# Core Protocol Messages
# ============================================================================

LOGON_REQUEST = 1
LOGON_RESPONSE = 2
HEARTBEAT = 3
LOGOFF = 4
ENCODING_REQUEST = 5
ENCODING_RESPONSE = 6

# ============================================================================
# Market Data Messages (100-199)
# ============================================================================

MARKET_DATA_REQUEST = 101
MARKET_DATA_REJECT = 103
MARKET_DATA_SNAPSHOT = 104
MARKET_DATA_UPDATE_TRADE = 107
MARKET_DATA_UPDATE_BID_ASK = 108
MARKET_DATA_UPDATE_SESSION_OPEN = 120
MARKET_DATA_UPDATE_SESSION_HIGH = 121
MARKET_DATA_UPDATE_SESSION_LOW = 122
MARKET_DATA_UPDATE_SESSION_VOLUME = 123
MARKET_DATA_UPDATE_OPEN_INTEREST = 124

# ============================================================================
# Order and Trade Messages (300-399)
# ============================================================================

SUBMIT_NEW_SINGLE_ORDER = 300
ORDER_UPDATE = 301
ORDER_CANCEL_REQUEST = 302
HISTORICAL_ORDER_FILLS_REQUEST = 303
HISTORICAL_ORDER_FILL_RESPONSE = 304
OPEN_ORDERS_REQUEST = 305
POSITION_UPDATE = 306
ORDER_FILL_RESPONSE = 307
NEW_ORDER_REQUEST = 308
ORDER_CANCEL_REPLACE_REQUEST = 310
ORDER_CANCEL_REJECT = 311
ORDER_REJECT = 312
ORDERS_CANCELLED_NOTIFICATION = 313

# ============================================================================
# Account Messages (400-699)
# ============================================================================

TRADE_ACCOUNTS_REQUEST = 400
TRADE_ACCOUNT_RESPONSE = 401
CURRENT_POSITIONS_REQUEST = 500
CURRENT_POSITIONS_REJECT = 502
ACCOUNT_BALANCE_REQUEST = 601
ACCOUNT_BALANCE_UPDATE = 600
ACCOUNT_BALANCE_REJECT = 602

# ============================================================================
# Historical Data Messages (700-799)
# ============================================================================

HISTORICAL_PRICE_DATA_REQUEST = 700
HISTORICAL_PRICE_DATA_RESPONSE_HEADER = 701
HISTORICAL_PRICE_DATA_RECORD_RESPONSE = 702
HISTORICAL_PRICE_DATA_TICK_RECORD_RESPONSE = 703
HISTORICAL_PRICE_DATA_REJECT = 704

# ============================================================================
# System Messages (800-899)
# ============================================================================

USER_MESSAGE = 800
GENERAL_LOG_MESSAGE = 801
ALERT_MESSAGE = 802
JOURNAL_ENTRY_ADD = 803

# ============================================================================
# Type Conversion Utilities
# ============================================================================

# Comprehensive type-to-name mapping
TYPE_TO_NAME = {
    # Core Protocol
    LOGON_REQUEST: "LogonRequest",
    LOGON_RESPONSE: "LogonResponse",
    HEARTBEAT: "Heartbeat",
    LOGOFF: "Logoff",
    ENCODING_REQUEST: "EncodingRequest",
    ENCODING_RESPONSE: "EncodingResponse",
    # Market Data
    MARKET_DATA_REQUEST: "MarketDataRequest",
    MARKET_DATA_REJECT: "MarketDataReject",
    MARKET_DATA_SNAPSHOT: "MarketDataSnapshot",
    MARKET_DATA_UPDATE_TRADE: "MarketDataUpdateTrade",
    MARKET_DATA_UPDATE_BID_ASK: "MarketDataUpdateBidAsk",
    MARKET_DATA_UPDATE_SESSION_OPEN: "MarketDataUpdateSessionOpen",
    MARKET_DATA_UPDATE_SESSION_HIGH: "MarketDataUpdateSessionHigh",
    MARKET_DATA_UPDATE_SESSION_LOW: "MarketDataUpdateSessionLow",
    MARKET_DATA_UPDATE_SESSION_VOLUME: "MarketDataUpdateSessionVolume",
    MARKET_DATA_UPDATE_OPEN_INTEREST: "MarketDataUpdateOpenInterest",
    # Orders & Trades
    SUBMIT_NEW_SINGLE_ORDER: "SubmitNewSingleOrder",
    ORDER_UPDATE: "OrderUpdate",
    ORDER_CANCEL_REQUEST: "OrderCancelRequest",
    HISTORICAL_ORDER_FILLS_REQUEST: "HistoricalOrderFillsRequest",
    HISTORICAL_ORDER_FILL_RESPONSE: "HistoricalOrderFillResponse",
    OPEN_ORDERS_REQUEST: "OpenOrdersRequest",
    POSITION_UPDATE: "PositionUpdate",
    ORDER_FILL_RESPONSE: "OrderFillResponse",
    NEW_ORDER_REQUEST: "NewOrderRequest",
    ORDER_CANCEL_REPLACE_REQUEST: "OrderCancelReplaceRequest",
    ORDER_CANCEL_REJECT: "OrderCancelReject",
    ORDER_REJECT: "OrderReject",
    ORDERS_CANCELLED_NOTIFICATION: "OrdersCancelledNotification",
    # Account Management
    TRADE_ACCOUNTS_REQUEST: "TradeAccountsRequest",
    TRADE_ACCOUNT_RESPONSE: "TradeAccountResponse",
    CURRENT_POSITIONS_REQUEST: "CurrentPositionsRequest",
    CURRENT_POSITIONS_REJECT: "CurrentPositionsReject",
    ACCOUNT_BALANCE_REQUEST: "AccountBalanceRequest",
    ACCOUNT_BALANCE_UPDATE: "AccountBalanceUpdate",
    ACCOUNT_BALANCE_REJECT: "AccountBalanceReject",
    # Historical Data
    HISTORICAL_PRICE_DATA_REQUEST: "HistoricalPriceDataRequest",
    HISTORICAL_PRICE_DATA_RESPONSE_HEADER: "HistoricalPriceDataResponseHeader",
    HISTORICAL_PRICE_DATA_RECORD_RESPONSE: "HistoricalPriceDataRecordResponse",
    HISTORICAL_PRICE_DATA_TICK_RECORD_RESPONSE: "HistoricalPriceDataTickRecordResponse",
    HISTORICAL_PRICE_DATA_REJECT: "HistoricalPriceDataReject",
    # System Messages
    USER_MESSAGE: "UserMessage",
    GENERAL_LOG_MESSAGE: "GeneralLogMessage",
    ALERT_MESSAGE: "AlertMessage",
    JOURNAL_ENTRY_ADD: "JournalEntryAdd",
}

# Reverse mapping (name to type)
NAME_TO_TYPE = {v: k for k, v in TYPE_TO_NAME.items()}


def type_to_name(msg_type: Union[int, str]) -> str:
    """
    Convert DTC message type to human-readable name.

    Args:
        msg_type: Integer type code or string name

    Returns:
        Human-readable message type name

    Examples:
        >>> type_to_name(1)
        'LogonRequest'
        >>> type_to_name("LogonRequest")
        'LogonRequest'
        >>> type_to_name(999)
        'Unknown_999'
    """
    if isinstance(msg_type, str):
        return msg_type

    if isinstance(msg_type, int):
        return TYPE_TO_NAME.get(msg_type, f"Unknown_{msg_type}")

    return f"Invalid_{type(msg_type).__name__}"


def name_to_type(msg_name: str) -> int:
    """
    Convert DTC message name to type code.

    Args:
        msg_name: Human-readable message type name

    Returns:
        Integer type code, or -1 if unknown

    Examples:
        >>> name_to_type("LogonRequest")
        1
        >>> name_to_type("Unknown")
        -1
    """
    return NAME_TO_TYPE.get(msg_name, -1)


def is_heartbeat(msg_type: Union[int, str]) -> bool:
    """Check if message is a heartbeat."""
    return msg_type == HEARTBEAT or msg_type == "Heartbeat"


def is_market_data(msg_type: int) -> bool:
    """Check if message is market data (100-199 range)."""
    return isinstance(msg_type, int) and 100 <= msg_type < 200


def is_order_message(msg_type: int) -> bool:
    """Check if message is order-related (300-399 range)."""
    return isinstance(msg_type, int) and 300 <= msg_type < 400


def is_account_message(msg_type: int) -> bool:
    """Check if message is account-related (400-699 range)."""
    return isinstance(msg_type, int) and 400 <= msg_type < 700


def is_historical_data(msg_type: int) -> bool:
    """Check if message is historical data (700-799 range)."""
    return isinstance(msg_type, int) and 700 <= msg_type < 800


# ============================================================================
# Protocol Constants
# ============================================================================

NULL_TERMINATOR = b"\x00"
DEFAULT_HEARTBEAT_INTERVAL = 5  # seconds
DEFAULT_PROTOCOL_VERSION = 8

# Trade modes
TRADE_MODE_DEMO = 0
TRADE_MODE_LIVE = 1
TRADE_MODE_SIMULATED = 2

# Order types
ORDER_TYPE_MARKET = 1
ORDER_TYPE_LIMIT = 2
ORDER_TYPE_STOP = 3
ORDER_TYPE_STOP_LIMIT = 4

# Buy/Sell
BUY_SELL_BUY = 1
BUY_SELL_SELL = 2

# Order status
ORDER_STATUS_OPEN = 1
ORDER_STATUS_FILLED = 2
ORDER_STATUS_CANCELED = 3
ORDER_STATUS_REJECTED = 4
ORDER_STATUS_PARTIALLY_FILLED = 5
