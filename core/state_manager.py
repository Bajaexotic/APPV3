from __future__ import annotations

import contextlib
from datetime import datetime

# File: core/state_manager.py
# Block 26/?? — StateManager with mode awareness (SIM/LIVE)
from typing import Any, Dict, Optional

from PyQt6 import QtCore


class StateManager(QtCore.QObject):
    """
    Lightweight app-wide state registry with advanced mode-aware position tracking.

    Maintains transient runtime data for panels, price feed, and
    account metrics. Should not store persistent data.

    Key Invariant: Only ONE active position at a time (SIM OR LIVE, not both)
    """

    # ===== SIGNALS =====
    balanceChanged = QtCore.pyqtSignal(float)  # Emitted when balance updates
    modeChanged = QtCore.pyqtSignal(str)  # Emitted when mode changes (SIM->LIVE or vice versa)

    def __init__(self):
        super().__init__()

        # Core dynamic store
        self._state: dict[str, Any] = {}

        # -------------------- mode awareness (start)
        self.current_account: Optional[str] = None
        self.is_sim_mode: bool = False
        self.current_mode: str = "SIM"  # "SIM", "LIVE", or "DEBUG"

        # Mode history: list of (timestamp_utc, mode, account) tuples
        self.mode_history: list[tuple[datetime, str, str]] = []
        self._add_to_mode_history(self.current_mode, self.current_account or "")

        self._log_mode_change("INIT", self.is_sim_mode)
        # -------------------- mode awareness (end)

        # ===== MODE-SPECIFIC BALANCE =====
        self.sim_balance: float = 10000.0  # SIM mode starting balance: $10K/month
        self.sim_balance_start_of_month: float = 10000.0  # Track starting balance for reset
        self.live_balance: float = 0.0

        # ===== POSITION TRACKING (MODE-AWARE) =====
        self.position_symbol: Optional[str] = None
        self.position_qty: float = 0  # positive = long, negative = short
        self.position_entry_price: float = 0
        self.position_entry_time: Optional[datetime] = None
        self.position_side: Optional[str] = None  # "LONG" or "SHORT"
        self.position_mode: Optional[str] = None  # "SIM" or "LIVE" - what mode this position is in

        # ===== ENTRY SNAPSHOTS (for closed trade record) =====
        self.entry_vwap: Optional[float] = None
        self.entry_cum_delta: Optional[float] = None
        self.entry_poc: Optional[float] = None
        self.entry_snapshot_time: Optional[datetime] = None

        # Config (injected)
        self.live_account_id: str = "120005"  # Will be set from config

    def load_sim_balance_from_trades(self) -> float:
        """
        Load the SIM balance from the database by summing all realized P&L trades.
        This is called on app startup to restore the balance if the app was restarted.
        """
        try:
            from data.db_engine import get_session
            from data.schema import TradeRecord
            from sqlalchemy import func

            print(f"[DEBUG state_manager.load_sim_balance_from_trades] Loading SIM balance from database...")

            with get_session() as session:
                # Query all closed trades in SIM mode and sum their realized P&L
                result = session.query(func.sum(TradeRecord.realized_pnl)).filter(
                    TradeRecord.mode == "SIM",
                    TradeRecord.realized_pnl != None,
                    TradeRecord.is_closed == True
                ).scalar()

                # Also count how many trades we have
                trade_count = session.query(TradeRecord).filter(
                    TradeRecord.mode == "SIM",
                    TradeRecord.is_closed == True
                ).count()

                total_pnl = float(result) if result else 0.0
                self.sim_balance = 10000.0 + total_pnl

                print(f"\n[DATABASE LOAD] SIM Balance Restored from Trades")
                print(f"  Trades in Database: {trade_count}")
                print(f"  Base Balance: $10,000.00")
                print(f"  Total P&L: {total_pnl:+,.2f}")
                print(f"  Current Balance: ${self.sim_balance:,.2f}\n")
                print(f"[DEBUG state_manager.load_sim_balance_from_trades] Total PnL from trades: {total_pnl:+,.2f}, SIM balance: ${self.sim_balance:,.2f}")

                return self.sim_balance
        except Exception as e:
            print(f"[DEBUG state_manager.load_sim_balance_from_trades] Error loading balance: {e}")
            # Fall back to default 10k
            self.sim_balance = 10000.0
            return self.sim_balance

    # ---- Core API ----
    def set(self, key: str, value: Any) -> None:
        """Assign a value to the state."""
        self._state[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a value or default."""
        return self._state.get(key, default)

    def delete(self, key: str) -> None:
        """Remove a key from the state."""
        if key in self._state:
            del self._state[key]

    def clear(self) -> None:
        """Clear all runtime state."""
        self._state.clear()

    # ---- Utility methods ----
    def dump(self) -> dict[str, Any]:
        """Return a shallow copy of state for debugging."""
        return dict(self._state)

    def keys(self):
        return list(self._state.keys())

    def update(self, mapping: dict[str, Any]) -> None:
        """Bulk update state."""
        self._state.update(mapping)

    # ---- Convenience accessors ----
    def get_active_symbol(self) -> Optional[str]:
        return self._state.get("active_symbol")

    def get_last_price(self) -> Optional[float]:
        return self._state.get("last_price")

    def get_positions(self) -> list[dict]:
        return self._state.get("positions", [])

    def set_positions(self, positions: list[dict]) -> None:
        self._state["positions"] = positions

    # -------------------- mode setter (start)
    def set_mode(self, account: str | None) -> None:
        """Detect and update simulation/live mode based on account string."""
        old_mode = self.is_sim_mode
        self.current_account = account
        new_mode = account.lower().startswith("sim") if account else False
        if new_mode != old_mode:
            self.is_sim_mode = new_mode
            # Detect mode string
            mode_str = "SIM" if new_mode else "LIVE"
            self._add_to_mode_history(mode_str, account or "")
            self._log_mode_change("Router", new_mode)

    # -------------------- mode setter (end)

    # -------------------- mode history tracking (start)
    def _add_to_mode_history(self, mode: str, account: str) -> None:
        """
        Add a mode change to history.

        Args:
            mode: Trading mode ("LIVE", "SIM", "DEBUG")
            account: Account identifier
        """
        from datetime import timezone
        timestamp_utc = datetime.now(timezone.utc)
        self.mode_history.append((timestamp_utc, mode, account))

        # Keep only last 100 mode changes to prevent memory bloat
        if len(self.mode_history) > 100:
            self.mode_history = self.mode_history[-100:]

    def get_mode_history(self, limit: Optional[int] = None) -> list[tuple[datetime, str, str]]:
        """
        Get mode change history.

        Args:
            limit: Optional limit on number of entries (most recent)

        Returns:
            List of (timestamp_utc, mode, account) tuples
        """
        if limit:
            return self.mode_history[-limit:]
        return list(self.mode_history)

    def get_last_mode_change(self) -> Optional[tuple[datetime, str, str]]:
        """
        Get the most recent mode change.

        Returns:
            Tuple of (timestamp_utc, mode, account) or None if no history
        """
        if self.mode_history:
            return self.mode_history[-1]
        return None

    def clear_mode_history(self) -> None:
        """Clear mode history (useful for testing)."""
        self.mode_history.clear()

    # -------------------- mode history tracking (end)

    # -------------------- mode logging (start)
    def _log_mode_change(self, src: str, mode: bool) -> None:
        """Internal helper for logging mode changes."""
        try:
            from utils.logger import get_logger

            log = get_logger("StateManager")
            label = "SIM" if mode else "LIVE"
            log.info(f"[Mode] {src}: Application now in {label} mode")
        except Exception:
            pass

    # -------------------- mode logging (end)

    # -------------------- Trading data persistence (start)
    def update_balance(self, balance: Optional[float]) -> None:
        """Record current account balance."""
        if balance is not None:
            with contextlib.suppress(TypeError, ValueError):
                self._state["balance"] = float(balance)  # Ignore invalid balance values

    def update_position(self, symbol: Optional[str], qty: int, avg_price: Optional[float]) -> None:
        """Record or remove a position."""
        if not symbol:
            return
        positions = self._state.get("positions", {})
        if qty == 0:
            # Close position (remove from dict)
            positions.pop(symbol, None)
        else:
            # Update or create position
            positions[symbol] = {
                "qty": int(qty),
                "avg_price": float(avg_price) if avg_price else None,
            }
        self._state["positions"] = positions

    def record_order(self, payload: dict) -> None:
        """Record an order event for statistics and replay."""
        if not isinstance(payload, dict):
            return
        orders = self._state.get("orders", [])
        orders.append(payload)
        self._state["orders"] = orders

    # -------------------- Trading data persistence (end)

    # ===== MODE MANAGEMENT =====
    @property
    def active_balance(self) -> float:
        """Return balance for the currently OPEN trade (not current_mode)"""
        if self.position_mode == "SIM":
            return self.sim_balance
        elif self.position_mode == "LIVE":
            return self.live_balance
        else:
            return self.get_balance_for_mode(self.current_mode)

    def get_balance_for_mode(self, mode: str) -> float:
        """Get balance for a specific mode"""
        return self.sim_balance if mode == "SIM" else self.live_balance

    def set_balance_for_mode(self, mode: str, balance: float) -> None:
        """Update balance for a specific mode"""
        print(f"[DEBUG state_manager.set_balance_for_mode] STEP 1: Called with mode={mode}, balance={balance}")
        if mode == "SIM":
            old_balance = self.sim_balance
            self.sim_balance = balance
            print(f"[DEBUG state_manager.set_balance_for_mode] STEP 2: SIM balance updated from {old_balance} to {balance}")
        else:
            old_balance = self.live_balance
            self.live_balance = balance
            print(f"[DEBUG state_manager.set_balance_for_mode] STEP 2: LIVE balance updated from {old_balance} to {balance}")

        # Emit signal so UI can update
        print(f"[DEBUG state_manager.set_balance_for_mode] STEP 3: Emitting balanceChanged signal with balance={balance}")
        self.balanceChanged.emit(balance)
        print(f"[DEBUG state_manager.set_balance_for_mode] STEP 4: Signal emitted successfully")

    def reset_sim_balance_to_10k(self) -> float:
        """Reset SIM balance to $10,000 (for monthly reset or manual hotkey)"""
        self.sim_balance = 10000.0
        self.sim_balance_start_of_month = 10000.0
        return self.sim_balance

    def adjust_sim_balance_by_pnl(self, realized_pnl: float) -> float:
        """
        Adjust SIM balance by realized P&L from a closed trade.

        Args:
            realized_pnl: The P&L from the closed trade (positive or negative)

        Returns:
            The new SIM balance after adjustment
        """
        try:
            realized_pnl_float = float(realized_pnl)
            self.sim_balance += realized_pnl_float

            from utils.logger import get_logger
            log = get_logger("StateManager")
            log.info(f"[SIM Balance] Adjusted by {realized_pnl_float:+,.2f} - New balance: ${self.sim_balance:,.2f}")

            return self.sim_balance
        except (TypeError, ValueError) as e:
            from utils.logger import get_logger
            log = get_logger("StateManager")
            log.error(f"[SIM Balance] Error adjusting balance: {e}")
            return self.sim_balance

    # ===== MODE DETECTION =====
    def detect_and_set_mode(self, account: str) -> str:
        """
        Detect trading mode from account string.
        Returns: "SIM", "LIVE", or "DEBUG"
        """
        if not account:
            mode = "DEBUG"
        elif account == self.live_account_id:  # e.g., "120005"
            mode = "LIVE"
        elif account.lower().startswith("sim"):
            mode = "SIM"
        else:
            mode = "DEBUG"

        # Only add to history if mode actually changed
        if mode != self.current_mode:
            self._add_to_mode_history(mode, account)

        self.current_mode = mode
        self.current_account = account
        return mode

    # ===== POSITION TRACKING =====
    def has_active_position(self) -> bool:
        """Check if ANY position is currently open"""
        return self.position_qty != 0

    def get_open_trade_mode(self) -> Optional[str]:
        """Returns what mode the current open trade is in (SIM, LIVE, or None)"""
        return self.position_mode if self.has_active_position() else None

    def is_mode_blocked(self, requested_mode: str) -> bool:
        """
        Check if switching to requested_mode is blocked due to open trade.

        Rules:
        1. LIVE mode cannot be blocked (always allowed)
        2. SIM mode blocked if LIVE position is open
        3. SIM mode allowed if SIM position is open (same mode)
        """
        if requested_mode == "LIVE":
            return False  # LIVE always takes precedence

        if requested_mode == "SIM":
            return self.position_mode == "LIVE"  # Blocked only if LIVE position open

        return False

    def open_position(self, symbol: str, qty: float, entry_price: float,
                      entry_time: datetime, mode: str) -> None:
        """Open a new position in the specified mode"""
        self.position_symbol = symbol
        self.position_qty = qty
        self.position_entry_price = entry_price
        self.position_entry_time = entry_time
        self.position_side = "LONG" if qty > 0 else "SHORT"
        self.position_mode = mode  # <-- KEY: Store what mode this position is in

    def close_position(self) -> Optional[dict]:
        """
        Close the current position and return the complete trade record.
        Called when position reaches qty = 0.
        """
        if not self.has_active_position():
            return None

        trade_record = {
            "symbol": self.position_symbol,
            "side": self.position_side,
            "qty": abs(self.position_qty),
            "entry_time": self.position_entry_time,
            "entry_price": self.position_entry_price,
            "entry_vwap": self.entry_vwap,
            "entry_cum_delta": self.entry_cum_delta,
            "mode": self.position_mode,  # <-- Record what mode this was
        }

        # Clear position
        self.position_symbol = None
        self.position_qty = 0
        self.position_entry_price = 0
        self.position_entry_time = None
        self.position_side = None
        self.position_mode = None

        # Clear snapshots
        self.entry_vwap = None
        self.entry_cum_delta = None
        self.entry_poc = None

        return trade_record

    def handle_mode_switch(self, new_mode: str) -> Optional[dict]:
        """
        Handle switching to a new mode.

        Rules:
        1. If switching to LIVE and SIM position is open -> close SIM position
        2. If switching to SIM and LIVE position is open -> DENY (block switch)
        3. If switching within same mode -> no-op

        Returns: Closed trade record (if any), or None
        """
        if new_mode == self.current_mode:
            return None  # No change

        if new_mode == "LIVE":
            # Switching to LIVE
            if self.position_mode == "SIM":
                # Close SIM position immediately
                closed_trade = self.close_position()
                self.current_mode = new_mode
                return closed_trade
            else:
                # No open position or already LIVE
                self.current_mode = new_mode
                return None

        elif new_mode == "SIM":
            # Switching to SIM
            if self.position_mode == "LIVE":
                # CANNOT switch - block it
                return None
            else:
                # No open position or already SIM
                self.current_mode = new_mode
                return None

        return None
