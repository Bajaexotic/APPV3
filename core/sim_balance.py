# -------------------- SIM Balance Manager (start) --------------------
"""
SIM mode balance tracker with account-scoped balances.
Tracks simulated account balance independently from live DTC balance.
Uses ledger-based balance calculation (start + realized_pnl - fees).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional

from utils.logger import get_logger


log = get_logger(__name__)

# Default SIM starting balance: $10,000 per account
SIM_STARTING_BALANCE: float = 10000.00


class SimBalanceManager:
    """
    Manages simulated trading balances with account-scoped storage.
    Each SIM account (Sim1, Sim2, etc.) has its own balance file.

    CRITICAL: Balance is ledger-derived (starting_balance + realized_pnl - fees).
    Do NOT depend on DTC balance updates for SIM mode.
    """

    def __init__(self):
        # Account-scoped balances: {account: balance}
        self._balances: dict[str, float] = {}
        # Track which accounts have been initialized
        self._initialized_accounts: set[str] = set()

    def _get_balance_file(self, account: str) -> Path:
        """Get account-scoped balance file path."""
        # Sanitize account for filename
        account_safe = "".join(c if c.isalnum() else "_" for c in account)
        return Path(__file__).parent.parent / "data" / f"sim_balance_{account_safe}.json"

    def _load(self, account: str) -> float:
        """
        Load persisted SIM balance for account.
        Returns starting balance if file doesn't exist.
        """
        balance_file = self._get_balance_file(account)

        try:
            if not balance_file.exists():
                log.debug(f"[SIM] No persisted balance for {account}, using starting balance")
                return SIM_STARTING_BALANCE

            with open(balance_file, encoding="utf-8") as f:
                data = json.load(f)

            balance = float(data.get("balance", SIM_STARTING_BALANCE))
            log.debug(f"[SIM] Loaded {account} balance: ${balance:,.2f}")
            return balance

        except Exception as e:
            log.warning(f"[SIM] Error loading balance file for {account}: {e}")
            return SIM_STARTING_BALANCE

    def _save(self, account: str, balance: float) -> None:
        """
        Persist SIM balance for account using atomic write.
        """
        try:
            from utils.atomic_persistence import save_json_atomic

            balance_file = self._get_balance_file(account)

            data = {
                "account": account,
                "balance": balance,
                "last_updated_utc": datetime.now(timezone.utc).isoformat(),
            }

            save_json_atomic(data, balance_file)
            log.debug(f"[SIM] Balance saved for {account}: ${balance:,.2f}")

        except Exception as e:
            log.error(f"[SIM] Error saving balance file for {account}: {e}")

    def get_balance(self, account: str) -> float:
        """
        Get current SIM balance for account.
        Lazily loads from disk if not in memory.

        Args:
            account: SIM account identifier (e.g., "Sim1")

        Returns:
            Current balance for account

        Example:
            balance = manager.get_balance("Sim1")
        """
        if account not in self._balances:
            # Load from disk
            self._balances[account] = self._load(account)
            self._initialized_accounts.add(account)

        return self._balances[account]

    def set_balance(self, account: str, balance: float) -> None:
        """
        Set SIM balance for account.

        Args:
            account: SIM account identifier
            balance: New balance

        Example:
            manager.set_balance("Sim1", 12000.0)
        """
        self._balances[account] = float(balance)
        self._save(account, balance)
        log.debug(f"[SIM] Balance updated for {account}: ${balance:,.2f}")

    def adjust_balance(self, account: str, delta: float) -> float:
        """
        Adjust balance by delta (positive or negative).

        Args:
            account: SIM account identifier
            delta: Amount to adjust (+ or -)

        Returns:
            New balance after adjustment

        Example:
            new_balance = manager.adjust_balance("Sim1", -250.0)  # Lost $250
        """
        current = self.get_balance(account)
        new_balance = current + delta
        self.set_balance(account, new_balance)
        log.info(f"[SIM] Balance adjusted for {account} by {delta:+,.2f} -> ${new_balance:,.2f}")
        return new_balance

    def reset_balance(self, account: str) -> float:
        """
        Manually reset SIM balance to starting balance.

        Args:
            account: SIM account identifier

        Returns:
            New balance (starting balance)

        Example:
            manager.reset_balance("Sim1")
        """
        self.set_balance(account, SIM_STARTING_BALANCE)
        log.info(f"[SIM] Manual reset for {account}: Balance reset to ${SIM_STARTING_BALANCE:,.2f}")
        return SIM_STARTING_BALANCE

    def get_all_accounts(self) -> list[str]:
        """
        Get list of all SIM accounts that have balances.

        Returns:
            List of account identifiers
        """
        return list(self._initialized_accounts)


# Global singleton instance
_sim_balance_manager: Optional[SimBalanceManager] = None


def get_sim_balance_manager() -> SimBalanceManager:
    """
    Get the global SIM balance manager singleton.
    """
    global _sim_balance_manager
    if _sim_balance_manager is None:
        _sim_balance_manager = SimBalanceManager()
    return _sim_balance_manager


# Convenience functions (account-scoped)
def get_sim_balance(account: str) -> float:
    """
    Get current SIM balance for account.

    Args:
        account: SIM account identifier (e.g., "Sim1")

    Returns:
        Current balance
    """
    return get_sim_balance_manager().get_balance(account)


def set_sim_balance(account: str, balance: float) -> None:
    """
    Set SIM balance for account.

    Args:
        account: SIM account identifier
        balance: New balance
    """
    get_sim_balance_manager().set_balance(account, balance)


def adjust_sim_balance(account: str, delta: float) -> float:
    """
    Adjust SIM balance by delta.

    Args:
        account: SIM account identifier
        delta: Amount to adjust

    Returns:
        New balance
    """
    return get_sim_balance_manager().adjust_balance(account, delta)


def reset_sim_balance(account: str) -> float:
    """
    Reset SIM balance to starting balance.

    Args:
        account: SIM account identifier

    Returns:
        Starting balance
    """
    return get_sim_balance_manager().reset_balance(account)


# -------------------- SIM Balance Manager (end) --------------------
