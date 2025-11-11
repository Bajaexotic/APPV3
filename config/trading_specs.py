# File: config/trading_specs.py
from __future__ import annotations

from typing import Dict, List, Optional


# ------------------------------------------------------------
# Centralized metric name sets for Panel 2 and Panel 3
# ------------------------------------------------------------

# Panel 2 (Live Position) metrics — tune as needed
PANEL2_METRICS: list[str] = [
    "Price",
    "Heat",
    "Time",
    "Target",
    "Stop",
    "Qty",
    "Avg",
    "MAE",
    "MFE",
    "R",
    "VWAP",
    "POC",
    "Delta",
    "ATR",
    "Notes",
]

# Panel 3 (Trading Stats / History) — example set
PANEL3_METRICS: list[str] = [
    "Total PnL",
    "Max Drawdown",
    "Max Run-Up",
    "Expectancy",
    "Avg Time",
    "Trades",
    "Best",
    "Worst",
    "Hit Rate",
    "Commissions",
    "Avg R",
    "Profit Factor",
    "Streak",
    "MAE",
    "MFE",
]

# ------------------------------------------------------------
# Futures spec map and helpers
# ------------------------------------------------------------

# Minimal tick/point/fees mapping — extend via config.json or env in app code if needed.
SPEC_OVERRIDES: dict[str, dict[str, float]] = {
    "ES": {"tick": 0.25, "pt_value": 50.00, "rt_fee": 4.50},
    "MES": {"tick": 0.25, "pt_value": 5.00, "rt_fee": 1.24},
    "NQ": {"tick": 0.25, "pt_value": 20.00, "rt_fee": 4.50},
    "MNQ": {"tick": 0.25, "pt_value": 2.00, "rt_fee": 1.24},
    "YM": {"tick": 1.00, "pt_value": 5.00, "rt_fee": 3.50},
    "MYM": {"tick": 1.00, "pt_value": 0.50, "rt_fee": 1.20},
}


def _root_from_symbol(symbol: Optional[str]) -> str:
    """
    Extract a root like 'ES' or 'MES' from symbols such as:
      - 'ESZ25'
      - 'F.US.ESZ25'
      - 'MESZ25'
    """
    s = (symbol or "").strip()
    if not s:
        return "ES"
    # Sierra style often includes prefixes like F.US.
    if "." in s:
        s = s.split(".")[-1]
    # Strip month/year code (last 2–3 chars) when present
    if len(s) > 3:
        return s[:-3]
    return s


def match_spec(symbol: Optional[str]) -> dict[str, float]:
    """Return a spec dict for the given symbol root; default to ES-like."""
    root = _root_from_symbol(symbol)
    return SPEC_OVERRIDES.get(root, {"tick": 0.25, "pt_value": 50.00, "rt_fee": 4.50})


def point_value_for(symbol: Optional[str]) -> float:
    return match_spec(symbol).get("pt_value", 50.0)


def tick_size_for(symbol: Optional[str]) -> float:
    return match_spec(symbol).get("tick", 0.25)


__all__ = [
    "PANEL2_METRICS",
    "PANEL3_METRICS",
    "SPEC_OVERRIDES",
    "match_spec",
    "point_value_for",
    "tick_size_for",
]
