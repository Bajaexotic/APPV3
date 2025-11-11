from __future__ import annotations

# File: services/trade_math.py
# Block 32/?? Ã¢â‚¬â€ TradeMath utility functions for PnL and trade stats
from typing import List, Tuple, Optional


class TradeMath:
    """
    Core math utility for trade statistics:
    - Realized PnL
    - Drawdown / Run-up
    - MFE / MAE
    - Expectancy
    - Helper functions (time formatting, sign conversion, etc)
    """

    @staticmethod
    def fmt_time_human(seconds: int) -> str:
        """Format seconds like '20s', '1:20s', '10:00s' (no spaces, always 's' suffix)."""
        if seconds < 60:
            return f"{seconds}s"
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}s"

    @staticmethod
    def sign_from_side(is_long: Optional[bool]) -> int:
        """Convert position direction to sign multiplier (1, -1, or 0)"""
        if is_long is True:
            return 1
        if is_long is False:
            return -1
        return 0

    @staticmethod
    def clamp(v: float, lo: float, hi: float) -> float:
        """Clamp value between lo and hi"""
        return max(lo, min(hi, v))

    @staticmethod
    def calculate_r_multiple(
        entry_price: float,
        exit_price: float,
        stop_price: float,
        qty: int,
        is_long: bool,
        dollars_per_point: float,
    ) -> Optional[float]:
        """
        Calculate R-multiple for a trade.

        R-multiple = Realized P&L / Initial Risk

        Args:
            entry_price: Entry price
            exit_price: Exit price (current or actual)
            stop_price: Stop loss price
            qty: Position quantity
            is_long: True if long, False if short
            dollars_per_point: Dollar value per point (e.g., 50 for ES)

        Returns:
            R-multiple or None if calculation not possible
        """
        if stop_price is None or float(stop_price) <= 0:
            return None

        sign = 1.0 if is_long else -1.0
        realized_pnl = (exit_price - entry_price) * sign * qty * dollars_per_point
        risk_per_contract = abs(entry_price - float(stop_price)) * dollars_per_point

        if risk_per_contract > 0:
            return realized_pnl / (risk_per_contract * qty)
        return None

    @staticmethod
    def calculate_mae_mfe(
        entry_price: float,
        trade_min_price: float,
        trade_max_price: float,
        is_long: bool,
        qty: int,
        dollars_per_point: float,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion).

        Args:
            entry_price: Entry price
            trade_min_price: Lowest price during trade
            trade_max_price: Highest price during trade
            is_long: True if long, False if short
            qty: Position quantity
            dollars_per_point: Dollar value per point

        Returns:
            Tuple of (MAE, MFE) in dollars, or (None, None) if calculation not possible
        """
        if trade_min_price is None or trade_max_price is None:
            return None, None

        try:
            if is_long:
                # Long: MAE = entry - trade_min (adverse = price fell), MFE = trade_max - entry (favorable = price rose)
                mae_pts = entry_price - trade_min_price
                mfe_pts = trade_max_price - entry_price
            else:
                # Short: MAE = trade_max - entry (adverse = price rose), MFE = entry - trade_min (favorable = price fell)
                mae_pts = trade_max_price - entry_price
                mfe_pts = entry_price - trade_min_price

            # Convert to positive magnitudes and dollars
            mae = abs(mae_pts) * dollars_per_point * qty
            mfe = abs(mfe_pts) * dollars_per_point * qty
            return mae, mfe
        except Exception:
            return None, None

    @staticmethod
    def realized_pnl(qty: float, entry: float, exit: float, pt_value: float) -> float:
        """Calculate realized PnL in USD."""
        try:
            diff = (exit - entry) * (1 if qty > 0 else -1)
            return diff * abs(qty) * pt_value
        except Exception:
            return 0.0

    @staticmethod
    def drawdown_runup(prices: list[float]) -> tuple[float, float]:
        """Return (max_drawdown, max_runup) based on a list of prices."""
        if not prices:
            return 0.0, 0.0
        max_dd, max_ru = 0.0, 0.0
        peak, trough = prices[0], prices[0]
        for p in prices:
            if p > peak:
                peak = p
            if p < trough:
                trough = p
            max_dd = max(max_dd, peak - p)
            max_ru = max(max_ru, p - trough)
        return max_dd, max_ru

    @staticmethod
    def mfe_mae(prices: list[float], entry_price: float) -> tuple[float, float]:
        """Return (MFE, MAE) Ã¢â‚¬â€ max favorable/adverse excursion."""
        if not prices:
            return 0.0, 0.0
        deltas = [p - entry_price for p in prices]
        mfe = max(deltas)
        mae = abs(min(deltas))
        return mfe, mae

    @staticmethod
    def expectancy(pnls: list[float]) -> float:
        """
        Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss)
        """
        if not pnls:
            return 0.0
        wins = [x for x in pnls if x > 0]
        losses = [abs(x) for x in pnls if x < 0]
        if not wins and not losses:
            return 0.0
        win_rate = len(wins) / len(pnls)
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
