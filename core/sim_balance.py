# -------------------- SIM Balance Manager (start) --------------------
"""
SIM mode balance tracker with monthly reset.
Tracks simulated account balance independently from live DTC balance.
Resets to $10,000 on the 1st of each month.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from utils.logger import get_logger


log = get_logger(__name__)

# Default SIM starting balance: $10,000 per month
SIM_STARTING_BALANCE: float = 10000.00

# Storage file for persistence across restarts (use absolute path relative to this file)
SIM_BALANCE_FILE: Path = Path(__file__).parent.parent / "data" / "sim_balance.json"


class SimBalanceManager:
    """
    Manages simulated trading balance with monthly auto-reset.
    """

    def __init__(self):
        self._balance: float = SIM_STARTING_BALANCE
        self._last_reset_month: Optional[str] = None  # Format: "YYYY-MM"
        self._load()
        self._check_monthly_reset()

    def _get_current_month(self) -> str:
        """Returns current month in YYYY-MM format."""
        return datetime.now().strftime("%Y-%m")

    def _check_monthly_reset(self) -> None:
        """
        Check if a new month has started and reset SIM balance to $10,000 if needed.
        This allows SIM mode to have a fresh $10K monthly allowance.
        """
        current_month = self._get_current_month()
        if self._last_reset_month != current_month:
            self._balance = SIM_STARTING_BALANCE
            self._last_reset_month = current_month
            self._save()
            log.info(f"[SIM] Monthly reset: Balance reset to ${self._balance:,.2f} for {current_month}")

    def get_balance(self) -> float:
        """
        Get current SIM balance. Checks for monthly reset first.
        """
        self._check_monthly_reset()
        return self._balance

    def set_balance(self, balance: float) -> None:
        """
        Set SIM balance (e.g., after a simulated trade).
        """
        self._balance = float(balance)
        self._save()
        log.debug(f"[SIM] Balance updated to ${self._balance:,.2f}")

    def adjust_balance(self, delta: float) -> float:
        """
        Adjust balance by delta (positive or negative).
        Returns new balance.
        """
        self._balance += delta
        self._save()
        log.debug(f"[SIM] Balance adjusted by {delta:+,.2f} -> ${self._balance:,.2f}")
        return self._balance

    def reset_balance(self) -> float:
        """
        Manually reset SIM balance to $10,000 (e.g., via Ctrl+Shift+R hotkey).
        Returns the new balance.
        """
        self._balance = SIM_STARTING_BALANCE
        self._last_reset_month = self._get_current_month()
        self._save()
        log.info(f"[SIM] Manual reset: Balance reset to ${self._balance:,.2f}")
        return self._balance

    def _load(self) -> None:
        """
        Load persisted SIM balance from file.
        """
        try:
            if not SIM_BALANCE_FILE.exists():
                log.debug("[SIM] No persisted balance file found, using defaults")
                self._last_reset_month = self._get_current_month()
                return

            with open(SIM_BALANCE_FILE, encoding="utf-8") as f:
                data = json.load(f)

            self._balance = float(data.get("balance", SIM_STARTING_BALANCE))
            self._last_reset_month = data.get("last_reset_month", self._get_current_month())

            log.debug(f"[SIM] Loaded balance: ${self._balance:,.2f}, last reset: {self._last_reset_month}")

        except Exception as e:
            log.warning(f"[SIM] Error loading balance file: {e}")
            self._balance = SIM_STARTING_BALANCE
            self._last_reset_month = self._get_current_month()

    def _save(self) -> None:
        """
        Persist SIM balance to file.
        """
        try:
            # Ensure data directory exists
            SIM_BALANCE_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "balance": self._balance,
                "last_reset_month": self._last_reset_month,
                "last_updated": datetime.now().isoformat(),
            }

            with open(SIM_BALANCE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            log.debug(f"[SIM] Balance saved: ${self._balance:,.2f}")

        except Exception as e:
            log.error(f"[SIM] Error saving balance file: {e}")


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


# Convenience functions
def get_sim_balance() -> float:
    """Get current SIM balance."""
    return get_sim_balance_manager().get_balance()


def set_sim_balance(balance: float) -> None:
    """Set SIM balance."""
    get_sim_balance_manager().set_balance(balance)


def adjust_sim_balance(delta: float) -> float:
    """Adjust SIM balance by delta. Returns new balance."""
    return get_sim_balance_manager().adjust_balance(delta)


def reset_sim_balance() -> None:
    """Reset SIM balance to $10k."""
    get_sim_balance_manager().reset_balance()


# -------------------- SIM Balance Manager (end) --------------------
