from __future__ import annotations

# File: utils/format_utils.py
# Block 16/?? Ã¢â‚¬â€ Formatting helpers (prices, money, durations)
from typing import Optional

from config.trading_specs import match_spec


def format_money(v: float) -> str:
    sign = "-" if (isinstance(v, (int, float)) and v < 0) else ""
    try:
        return f"{sign}${abs(float(v)):, .2f}".replace(" ,", ",")
    except Exception:
        return "Ã¢â‚¬â€"


def format_price(symbol: Optional[str], price: Optional[float]) -> str:
    """Format price to the instrument's tick precision."""
    try:
        if price is None:
            return "Ã¢â‚¬â€"
        tick = match_spec(symbol).get("tick", 0.25)
        # determine decimals from tick size (e.g., 0.25 -> 2)
        s = f"{tick:.10f}".rstrip("0").rstrip(".")
        dec = len(s.split(".")[1]) if "." in s else 0
        return f"{float(price):.{dec}f}"
    except Exception:
        return "Ã¢â‚¬â€"


def hms(seconds: float) -> str:
    """Return H:MM:SS for a duration in seconds."""
    try:
        s = max(0, int(seconds))
        h = s // 3600
        m = (s % 3600) // 60
        s = s % 60
        return f"{h}:{m:02d}:{s:02d}"
    except Exception:
        return "0:00:00"


def mmss(seconds: float) -> str:
    """Return MM:SS for short durations."""
    try:
        s = max(0, int(seconds))
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "00:00"
