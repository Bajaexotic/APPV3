from __future__ import annotations

from datetime import datetime
from typing import Optional


def record_closed_trade(
    *,
    symbol: str,
    side: str,
    qty: int,
    entry_price: float,
    exit_price: float,
    realized_pnl: float,
    entry_time: Optional[datetime] = None,
    exit_time: Optional[datetime] = None,
    commissions: Optional[float] = None,
    r_multiple: Optional[float] = None,
    mae: Optional[float] = None,
    mfe: Optional[float] = None,
) -> bool:
    """Persist a closed trade into the DB (TradeRecord). Returns True on success."""
    try:
        from data.db_engine import get_session
        from data.schema import TradeRecord
    except Exception:
        return False

    try:
        with get_session() as s:  # type: ignore
            rec = TradeRecord(
                symbol=symbol,
                side=side,
                qty=int(qty),
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                realized_pnl=float(realized_pnl),
                entry_time=entry_time,
                exit_time=exit_time or datetime.utcnow(),
                commissions=commissions,
                r_multiple=r_multiple,
                mae=mae,
                mfe=mfe,
            )
            s.add(rec)
            s.commit()
        return True
    except Exception:
        return False
