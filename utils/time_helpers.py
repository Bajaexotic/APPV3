from __future__ import annotations

import datetime as dt

# File: utils/time_helpers.py
# Time utilities for epoch timestamps and formatting
import time
from typing import Union


# -------------------- Current Time --------------------


def now_epoch() -> float:
    """Return current time in UNIX epoch seconds."""
    return time.time()


# -------------------- Epoch to String Formatters --------------------


def epoch_to_str(ts: float) -> str:
    """Convert epoch timestamp to ISO-like human-readable string.

    Args:
        ts: Epoch timestamp (seconds since 1970-01-01)

    Returns:
        String in format "YYYY-MM-DD HH:MM:SS" or "—" on error
    """
    try:
        return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"


def fmt_time(epoch: Union[int, float], fmt: str = "%H:%M:%S") -> str:
    """Format epoch seconds into readable time string with custom format.

    Args:
        epoch: Epoch timestamp
        fmt: strftime format string (default: "%H:%M:%S")

    Returns:
        Formatted time string or "—" on error
    """
    try:
        return time.strftime(fmt, time.localtime(epoch))
    except Exception:
        return "—"


def fmt_date(epoch: Union[int, float], fmt: str = "%Y-%m-%d") -> str:
    """Format epoch seconds to date string with custom format.

    Args:
        epoch: Epoch timestamp
        fmt: strftime format string (default: "%Y-%m-%d")

    Returns:
        Formatted date string or "—" on error
    """
    try:
        return time.strftime(fmt, time.localtime(epoch))
    except Exception:
        return "—"


def format_short_date(ts: float) -> str:
    """Return concise date format (MM/DD HH:MM).

    Args:
        ts: Epoch timestamp

    Returns:
        String in format "MM/DD HH:MM" or "—" on error
    """
    try:
        return dt.datetime.fromtimestamp(ts).strftime("%m/%d %H:%M")
    except Exception:
        return "—"


# -------------------- Time Delta Formatters --------------------


def since(ts: float) -> str:
    """Return time delta (H:MM:SS) since timestamp.

    Args:
        ts: Epoch timestamp to measure from

    Returns:
        String in format "H:MM:SS" or "0:00:00" on error
    """
    try:
        delta = int(time.time() - ts)
        h = delta // 3600
        m = (delta % 3600) // 60
        s = delta % 60
        return f"{h}:{m:02d}:{s:02d}"
    except Exception:
        return "0:00:00"


def elapsed_since(epoch: Union[int, float]) -> str:
    """Return human-readable elapsed time (e.g., '2h 15m' or '45s').

    Args:
        epoch: Epoch timestamp to measure from

    Returns:
        Human-readable string like "2h 15m", "5m 30s", or "45s"
    """
    try:
        delta = max(0.0, time.time() - float(epoch))
        mins, secs = divmod(int(delta), 60)
        hrs, mins = divmod(mins, 60)
        if hrs:
            return f"{hrs}h {mins}m"
        if mins:
            return f"{mins}m {secs}s"
        return f"{secs}s"
    except Exception:
        return "—"


# -------------------- Special Time Calculations --------------------


def midnight_epoch(offset_days: int = 0) -> float:
    """Return epoch of local midnight ± offset days.

    Args:
        offset_days: Number of days to offset from today (0 = today's midnight)

    Returns:
        Epoch timestamp of midnight on the specified day
    """
    dt_midnight = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if offset_days:
        dt_midnight += dt.timedelta(days=offset_days)
    return dt_midnight.timestamp()


# -------------------- Exports --------------------

__all__ = [
    "now_epoch",
    "epoch_to_str",
    "fmt_time",
    "fmt_date",
    "format_short_date",
    "since",
    "elapsed_since",
    "midnight_epoch",
]
