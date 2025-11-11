# -------------------- trade_logger.py (start)
"""
Trade Logger Service
Logs all live trades (opens and closes) to the database for historical analysis.
Panel 3 uses this data to calculate statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from utils.logger import get_logger


log = get_logger(__name__)


class TradeLogger:
    """
    Captures position opens and closes, logs them as completed trades to the database.
    Tracks entry/exit prices, P&L, commissions, and quality metrics.
    """

    def __init__(self):
        self._open_positions: dict[str, dict[str, Any]] = {}  # symbol -> {qty, entry_price, entry_time, ...}
        self._account = "UNKNOWN"

    def set_account(self, account: str) -> None:
        """Set the current trading account (LIVE, SIM1, etc)."""
        self._account = account
        log.info(f"trade_logger.account.{account}")

    def on_position_update(self, payload: dict[str, Any]) -> None:
        """
        Called when a position update (Type 306) arrives from DTC.
        Logs opens when qty goes from 0 to N.
        Logs closes when qty goes from N to 0.
        """
        symbol = payload.get("symbol")
        qty = payload.get("qty", 0)
        avg_entry = payload.get("avg_entry")
        trade_account = payload.get("TradeAccount")

        if not symbol:
            return

        current_pos = self._open_positions.get(symbol)

        # OPEN: qty increased (or went from 0 to qty)
        if qty > 0 and (not current_pos or current_pos["qty"] == 0):
            log.info(
                "trade.open",
                symbol=symbol,
                qty=qty,
                entry_price=avg_entry,
                account=self._account,
            )
            self._open_positions[symbol] = {
                "qty": qty,
                "entry_price": avg_entry,
                "entry_time": datetime.utcnow(),
                "trade_account": trade_account,
                "account": self._account,
            }

        # CLOSE: qty went to 0
        elif qty == 0 and current_pos and current_pos["qty"] > 0:
            log.info(
                "trade.close",
                symbol=symbol,
                original_qty=current_pos["qty"],
                entry_price=current_pos["entry_price"],
                account=self._account,
            )
            self._log_trade_to_db(symbol, current_pos)
            self._open_positions.pop(symbol, None)

        # UPDATE: qty changed but didn't close
        elif qty > 0 and current_pos:
            if qty != current_pos["qty"]:
                log.debug("trade.partial_close", symbol=symbol, old_qty=current_pos["qty"], new_qty=qty)
                self._open_positions[symbol]["qty"] = qty

    def on_order_fill(self, payload: dict[str, Any]) -> None:
        """
        Called when an order fill (Type 307) arrives.
        Can be used to supplement position tracking with fill prices.
        """
        symbol = payload.get("Symbol")
        filled_qty = payload.get("FilledQuantity", 0)
        fill_price = payload.get("Price") or payload.get("AverageFillPrice")

        if symbol and filled_qty > 0 and fill_price:
            log.debug(
                "trade.fill",
                symbol=symbol,
                qty=filled_qty,
                price=fill_price,
                account=self._account,
            )

    def _log_trade_to_db(self, symbol: str, pos_info: dict[str, Any]) -> None:
        """
        Save a closed trade to the database for historical analysis.
        """
        try:
            from data.db_engine import get_session
            from data.schema import TradeRecord
        except Exception as e:
            log.error("trade_logger.db_import_failed", err=str(e))
            return

        try:
            trade = TradeRecord(
                symbol=symbol,
                side="LONG",  # Will be refined based on qty sign later
                qty=pos_info.get("qty", 0),
                entry_price=pos_info.get("entry_price", 0.0),
                entry_time=pos_info.get("entry_time", datetime.utcnow()),
                # Exit info would be populated when position closes
                exit_price=None,  # Would be set when we know the close price
                exit_time=datetime.utcnow(),
                is_closed=True,
                account=pos_info.get("account", self._account),
                trade_account=pos_info.get("trade_account"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            with get_session() as s:
                s.add(trade)
                s.commit()
                log.info(
                    "trade.logged",
                    symbol=symbol,
                    qty=pos_info.get("qty"),
                    entry_price=pos_info.get("entry_price"),
                    trade_id=trade.id,
                )
        except Exception as e:
            log.error("trade_logger.db_write_failed", symbol=symbol, err=str(e))


# -------------------- trade_logger.py (end)
