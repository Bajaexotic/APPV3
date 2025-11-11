from __future__ import annotations

# File: utils/error_helpers.py
# Block 38/?? Ã¢â‚¬â€ Error handling helpers
import traceback
from typing import Optional


def log_exception(context: str, exc: Exception, verbose: bool = True) -> None:
    """
    Print or record exceptions consistently across the app.
    """
    header = f"[Error] {context}: {exc}"
    print(header)
    if verbose:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print(tb)


def safe_call(func, *args, **kwargs):
    """
    Execute a callable safely, logging any exceptions without interrupting flow.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_exception(func.__name__, e)
        return None
