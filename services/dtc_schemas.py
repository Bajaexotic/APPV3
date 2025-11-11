"""
services/dtc_schemas.py

Pydantic models for DTC (Data and Trading Communications) protocol messages.
Provides type-safe validation and parsing for Sierra Chart JSON messages.

Reference: DTC Protocol Documentation

Field Alias Information
======================

The DTC protocol messages from Sierra Chart may use different field names
for the same logical data, depending on the Sierra Chart version. This schema
handles all known variants using field aliases.

Common Alias Groups:
- Quantity: OrderQuantity, Quantity, TotalQuantity (use get_quantity())
- Price: Price1, Price, LimitPrice, StopPrice (use get_price())
- Average Fill Price: AverageFillPrice, AvgFillPrice (use get_avg_fill_price())
- High/Low During Position: HighDuringPosition, HighPriceDuringPosition (use get_high/low_during_position())
- Text: InfoText, TextMessage, FreeFormText, RejectText (use get_text())

The helper methods at the end of the OrderUpdate class automatically coalesce
these aliases with priority ordering to simplify data extraction.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==================== DTC Enums ====================


class BuySellEnum(IntEnum):
    """DTC BuySell field values"""

    BUY = 1
    SELL = 2


class OrderTypeEnum(IntEnum):
    """DTC OrderType field values"""

    MARKET = 1
    LIMIT = 2
    STOP = 3
    STOP_LIMIT = 4
    MARKET_IF_TOUCHED = 5


class OrderStatusEnum(IntEnum):
    """DTC OrderStatus field values"""

    ORDER_STATUS_UNSPECIFIED = 0
    ORDER_STATUS_NEW = 1
    ORDER_STATUS_SUBMITTED = 2
    ORDER_STATUS_PENDING_CANCEL = 3
    ORDER_STATUS_OPEN = 4
    ORDER_STATUS_PENDING_REPLACE = 5
    ORDER_STATUS_CANCELED = 6
    ORDER_STATUS_FILLED = 7
    ORDER_STATUS_REJECTED = 8
    ORDER_STATUS_PARTIALLY_FILLED = 9


class OrderUpdateReasonEnum(IntEnum):
    """DTC OrderUpdateReason field values"""

    UNKNOWN = 0
    NEW_ORDER_ACCEPTED = 1
    GENERAL_ORDER_UPDATE = 2
    ORDER_FILLED = 3
    ORDER_FILLED_PARTIALLY = 4
    ORDER_CANCELED = 5
    ORDER_CANCEL_REPLACE_COMPLETE = 6
    NEW_ORDER_REJECTED = 7
    ORDER_CANCEL_REJECTED = 8
    ORDER_CANCEL_REPLACE_REJECTED = 9


class PositionUpdateReasonEnum(IntEnum):
    """DTC PositionUpdate UpdateReason"""

    UNSOLICITED = 0
    CURRENT_POSITIONS_REQUEST_RESPONSE = 1
    POSITIONS_REQUEST_RESPONSE = 2


# ==================== Base DTC Message ====================


class DTCMessage(BaseModel):
    """Base class for all DTC messages"""

    Type: Optional[int] = Field(
        None, description="DTC message type number (optional since normalized payloads may strip it)"
    )

    # Pydantic v2 config
    model_config = ConfigDict(extra="allow", use_enum_values=True)


# ==================== Order Messages (Type 300-313) ====================


class OrderUpdate(DTCMessage):
    """
    Type 301 - OrderUpdate
    Most important message for order tracking and ledger building.
    """

    Type: Optional[Literal[301]] = None  # Optional since normalized payloads may strip Type

    # Identity
    ServerOrderID: Optional[str] = None
    ClientOrderID: Optional[str] = None
    TradeAccount: Optional[str] = None

    # Symbol
    Symbol: Optional[str] = None
    Exchange: Optional[str] = None

    # Order details
    BuySell: Optional[int] = None  # BuySellEnum
    OrderType: Optional[int] = None  # OrderTypeEnum
    OrderStatus: Optional[int] = None  # OrderStatusEnum
    OrderUpdateReason: Optional[int] = None  # OrderUpdateReasonEnum

    # Quantities (use get_quantity() helper to coalesce)
    # Priority: OrderQuantity > Quantity > TotalQuantity
    OrderQuantity: Optional[float] = None  # Primary field (use this for new orders)
    Quantity: Optional[float] = None  # Alias for OrderQuantity (may appear from older Sierra versions)
    TotalQuantity: Optional[float] = None  # Alias for OrderQuantity (may appear from some DTC servers)
    FilledQuantity: Optional[float] = None  # Amount actually filled
    RemainingQuantity: Optional[float] = None  # Amount still open

    # Prices (use get_price() helper to coalesce)
    # Priority: Price1 > Price > LimitPrice > StopPrice
    # Note: Price2 is different (secondary/limit price for stop-limit orders)
    Price1: Optional[float] = None  # Primary price field (limit/stop/trigger price)
    Price2: Optional[float] = None  # Secondary price (limit price for stop-limit orders only)
    Price: Optional[float] = None  # Alias for Price1 (may appear from older Sierra versions)
    LimitPrice: Optional[float] = None  # Alias for Price1 (semantic when order is limit type)
    StopPrice: Optional[float] = None  # Alias for Price1 (semantic when order is stop type)

    # Fill details
    AverageFillPrice: Optional[float] = None  # Weighted average fill price
    AvgFillPrice: Optional[float] = None  # Alias for AverageFillPrice
    LastFillPrice: Optional[float] = None  # Price of most recent fill
    LastFillQuantity: Optional[float] = None  # Quantity of last fill
    LastFillDateTime: Optional[float] = None  # Unix timestamp (seconds) of last fill

    # Position extremes during order lifetime
    HighDuringPosition: Optional[float] = None  # High price during order lifetime
    HighPriceDuringPosition: Optional[float] = None  # Alias for HighDuringPosition
    LowDuringPosition: Optional[float] = None  # Low price during order lifetime
    LowPriceDuringPosition: Optional[float] = None  # Alias for LowDuringPosition

    # Timestamps (Unix epoch time in seconds since 1970-01-01 00:00:00 UTC)
    # To convert to datetime: datetime.fromtimestamp(timestamp, tz=timezone.utc)
    # Example: 1730822500.0 = Nov 5, 2024 at 5:01:40 PM UTC
    OrderReceivedDateTime: Optional[float] = None  # Unix timestamp (seconds), order received time
    LatestTransactionDateTime: Optional[float] = None  # Unix timestamp (seconds), most recent update time

    # Text/Info (use get_text() helper to coalesce)
    # Priority: InfoText > TextMessage > FreeFormText > RejectText
    InfoText: Optional[str] = None  # General information text
    TextMessage: Optional[str] = None  # Alias for text field (may appear from older Sierra versions)
    FreeFormText: Optional[str] = None  # Another alias for text field
    RejectText: Optional[str] = None  # Rejection reason when applicable

    # Sequencing (for initial seed responses)
    MessageNumber: Optional[int] = None  # Message index in batch response
    TotalNumberMessages: Optional[int] = None  # Total messages in batch
    TotalNumMessages: Optional[int] = None  # Alias for TotalNumberMessages
    NoOrders: Optional[int] = None  # Flag: 1 = no orders available

    # Unsolicited flag
    Unsolicited: Optional[int] = None  # 1 = live update, 0 = response to request

    # Request correlation (for request/response pattern)
    # Note: RequestID=0 typically indicates unsolicited broadcast from server
    RequestID: Optional[int] = None  # Links response to request; 0 = unsolicited

    @field_validator("BuySell", mode="before")
    @classmethod
    def validate_buy_sell(cls, v):
        """Validate BuySell is 1 (BUY) or 2 (SELL)"""
        if v is not None and v not in [1, 2]:
            return None
        return v

    @field_validator("OrderType", mode="before")
    @classmethod
    def validate_order_type(cls, v):
        """Validate OrderType is 1-5 (Market, Limit, Stop, StopLimit, MIT)"""
        if v is not None and v not in [1, 2, 3, 4, 5]:
            return None
        return v

    @field_validator("OrderStatus", mode="before")
    @classmethod
    def validate_order_status(cls, v):
        """Validate OrderStatus is 0-9 (valid DTC order statuses)"""
        if v is not None and v not in range(0, 10):
            return None
        return v

    @field_validator("OrderUpdateReason", mode="before")
    @classmethod
    def validate_order_update_reason(cls, v):
        """Validate OrderUpdateReason is 0-9 (valid DTC update reasons)"""
        if v is not None and v not in range(0, 10):
            return None
        return v

    def get_side(self) -> Optional[str]:
        """Returns 'Buy' or 'Sell'"""
        if self.BuySell == 1:
            return "Buy"
        elif self.BuySell == 2:
            return "Sell"
        return None

    def get_order_type(self) -> Optional[str]:
        """Returns human-readable order type"""
        type_map = {1: "Market", 2: "Limit", 3: "Stop", 4: "StopLimit", 5: "MIT"}
        return type_map.get(self.OrderType)

    def get_status(self) -> Optional[str]:
        """Returns human-readable order status"""
        status_map = {
            1: "New",
            2: "Submitted",
            3: "PendingCancel",
            4: "Open",
            5: "PendingReplace",
            6: "Canceled",
            7: "Filled",
            8: "Rejected",
            9: "PartiallyFilled",
        }
        return status_map.get(self.OrderStatus)

    def get_reason(self) -> Optional[str]:
        """Returns human-readable update reason"""
        reason_map = {
            1: "NewAccepted",
            2: "GeneralUpdate",
            3: "Filled",
            4: "PartialFill",
            5: "Canceled",
            6: "ReplaceComplete",
            7: "Rejected",
            8: "CancelRejected",
            9: "ReplaceRejected",
        }
        return reason_map.get(self.OrderUpdateReason)

    def is_terminal(self) -> bool:
        """Returns True if order is in terminal state (Filled, Canceled, Rejected)"""
        return self.OrderStatus in [6, 7, 8]

    def is_fill_update(self) -> bool:
        """Returns True if this is a fill update"""
        return self.OrderUpdateReason in [3, 4] or self.OrderStatus == 7

    def get_quantity(self) -> Optional[float]:
        """Coalesces quantity fields"""
        return self.OrderQuantity or self.Quantity or self.TotalQuantity

    def get_price(self) -> Optional[float]:
        """Coalesces price fields"""
        return self.Price1 or self.Price or self.LimitPrice or self.StopPrice

    def get_avg_fill_price(self) -> Optional[float]:
        """Coalesces average fill price fields"""
        return self.AverageFillPrice or self.AvgFillPrice

    def get_high_during_position(self) -> Optional[float]:
        """Coalesces high during position fields"""
        return self.HighDuringPosition or self.HighPriceDuringPosition

    def get_low_during_position(self) -> Optional[float]:
        """Coalesces low during position fields"""
        return self.LowDuringPosition or self.LowPriceDuringPosition

    def get_timestamp(self) -> Optional[float]:
        """
        Returns best available timestamp (Unix seconds since epoch).

        Priority: LatestTransactionDateTime > OrderReceivedDateTime

        Format: Unix epoch time in seconds since 1970-01-01 00:00:00 UTC
        Example: 1730822500.0 = Nov 5, 2024 at 5:01:40 PM UTC

        To convert to datetime:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        """
        return self.LatestTransactionDateTime or self.OrderReceivedDateTime

    def get_text(self) -> Optional[str]:
        """
        Coalesces text/info fields with priority ordering.

        Priority: InfoText > TextMessage > FreeFormText > RejectText
        """
        return self.InfoText or self.TextMessage or self.FreeFormText or self.RejectText


class HistoricalOrderFillResponse(DTCMessage):
    """Type 304 - Historical order fill"""

    Type: Optional[Literal[304]] = None  # Optional since normalized payloads may strip Type

    ServerOrderID: Optional[str] = None
    Symbol: Optional[str] = None
    TradeAccount: Optional[str] = None
    BuySell: Optional[int] = None
    Quantity: Optional[float] = None
    Price: Optional[float] = None
    DateTime: Optional[float] = None
    Profit: Optional[float] = None
    Commission: Optional[float] = None

    def get_side(self) -> Optional[str]:
        return "Buy" if self.BuySell == 1 else "Sell" if self.BuySell == 2 else None


# ==================== Position Messages (Type 306, 500) ====================


class PositionUpdate(DTCMessage):
    """Type 306 - Position update"""

    Type: Optional[Literal[306]] = None  # Optional since normalized payloads may strip Type

    # Identity
    TradeAccount: Optional[str] = None
    Symbol: Optional[str] = None
    Exchange: Optional[str] = None

    # Position data
    Quantity: Optional[float] = None
    AveragePrice: Optional[float] = None
    OpenProfitLoss: Optional[float] = None
    DailyProfitLoss: Optional[float] = None

    # Extremes
    HighPriceDuringPosition: Optional[float] = None
    LowPriceDuringPosition: Optional[float] = None

    # Metadata
    UpdateReason: Optional[
        int
    ] = None  # Maps to PositionUpdateReasonEnum (0=Unsolicited, 1=CurrentPositionsResponse, 2=PositionsResponse)
    Unsolicited: Optional[int] = None

    # Sequencing
    MessageNumber: Optional[int] = None
    TotalNumberMessages: Optional[int] = None
    TotalNumMessages: Optional[int] = None
    NoPositions: Optional[int] = None

    # Accept string aliases for UpdateReason (e.g., "Unsolicited")
    @field_validator("UpdateReason", mode="before")
    @classmethod
    def normalize_update_reason(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v if v in (0, 1, 2) else None
        if isinstance(v, str):
            s = v.strip().lower()
            mapping = {
                "unsolicited": 0,
                "currentpositionsresponse": 1,
                "currentpositionsrequestresponse": 1,
                "positionsresponse": 2,
                "positionsrequestresponse": 2,
            }
            return mapping.get(s, None)
        return None


# ==================== Account Messages (Type 400, 401, 600, 601) ====================


class TradeAccountResponse(DTCMessage):
    """Type 401 - Trade account information"""

    Type: Optional[Literal[401]] = None  # Optional since normalized payloads may strip Type

    TradeAccount: Optional[str] = None
    AccountName: Optional[str] = None
    RequestID: Optional[int] = None


class AccountBalanceUpdate(DTCMessage):
    """Type 600 - Account balance update"""

    Type: Optional[Literal[600]] = None  # Optional since normalized payloads may strip Type

    TradeAccount: Optional[str] = None
    CashBalance: Optional[float] = None
    BalanceAvailableForNewPositions: Optional[float] = None
    AccountValue: Optional[float] = None  # Net liquidating value
    NetLiquidatingValue: Optional[float] = None  # Alias
    AvailableFunds: Optional[float] = None
    MarginRequirement: Optional[float] = None
    SecuritiesValue: Optional[float] = None
    OpenPositionsProfitLoss: Optional[float] = None
    DailyProfitLoss: Optional[float] = None
    DailyNetLossLimit: Optional[float] = None
    TrailingAccountValueToLimitPositions: Optional[float] = None

    RequestID: Optional[int] = None
    MessageNumber: Optional[int] = None
    TotalNumberMessages: Optional[int] = None
    Unsolicited: Optional[int] = None


# ==================== Message Type Registry ====================

DTC_MESSAGE_REGISTRY = {
    301: OrderUpdate,
    304: HistoricalOrderFillResponse,
    306: PositionUpdate,
    401: TradeAccountResponse,
    600: AccountBalanceUpdate,
}


def parse_dtc_message(raw: dict) -> DTCMessage:
    """
    Parse a raw DTC message dict into appropriate Pydantic model.
    Falls back to generic DTCMessage if type not recognized.

    Args:
        raw: Raw DTC message dictionary

    Returns:
        Parsed Pydantic model instance

    Example:
        >>> msg = {"Type": 301, "ServerOrderID": "12345", "Symbol": "MESZ24"}
        >>> order = parse_dtc_message(msg)
        >>> isinstance(order, OrderUpdate)
        True
    """
    msg_type = raw.get("Type")
    model_class = DTC_MESSAGE_REGISTRY.get(msg_type, DTCMessage)

    try:
        return model_class.model_validate(raw)
    except Exception as e:
        # Validation failed, return generic with error metadata
        generic = DTCMessage.model_validate(raw)
        setattr(generic, "_parse_error", str(e))
        return generic
