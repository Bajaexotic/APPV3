# -------------------- CLEAN SCHEMA (start)
"""
Clean DTC schema based on what Sierra Chart ACTUALLY sends:
- Type 401: TradeAccountResponse
- Type 501: MktDataResponse (market data, NOT positions)
- Type 600: AccountBalanceUpdate
- Type 3: Heartbeat

NO position data comes from Sierra - it only sends market data.
All position tracking must be INFERRED from order executions.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TradeRecord(SQLModel, table=True):
    """Complete trade record - entry to exit"""

    id: Optional[int] = Field(default=None, primary_key=True)

    # Trade identification
    symbol: str
    side: str  # "LONG" or "SHORT"
    qty: int

    # Entry
    entry_time: datetime = Field(default_factory=datetime.utcnow, index=True)
    entry_price: float

    # Exit (empty until position is closed)
    exit_time: Optional[datetime] = Field(default=None, index=True)
    exit_price: Optional[float] = None
    is_closed: bool = Field(default=False)

    # P&L
    realized_pnl: Optional[float] = None
    commissions: Optional[float] = None

    # Trade quality
    r_multiple: Optional[float] = None
    mae: Optional[float] = None
    mfe: Optional[float] = None

    # Account info
    account: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderRecord(SQLModel, table=True):
    """Order records for trade reconstruction"""

    id: Optional[int] = Field(default=None, primary_key=True)

    order_id: str = Field(index=True)
    symbol: str = Field(index=True)
    side: str  # "BUY" or "SELL"
    qty: int
    price: float

    filled_qty: int = Field(default=0)
    filled_price: Optional[float] = None
    status: str  # "PENDING", "FILLED", "CANCELLED"

    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    account: Optional[str] = None


class AccountBalance(SQLModel, table=True):
    """Account balance snapshots"""

    id: Optional[int] = Field(default=None, primary_key=True)

    account_id: str = Field(index=True)
    balance: float
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)


# -------------------- CLEAN SCHEMA (end)
