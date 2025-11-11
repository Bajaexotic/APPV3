# -------------------- logger (start)
"""
utils/logger.py
Unified logger for APPSIERRA: handles console + file output with rotation,
respects DEBUG_MODE from config/settings.py, and provides a standard
get_logger() accessor for all modules and services.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Optional

from config.settings import DEBUG_MODE, TRADING_MODE


def _init_logger_system() -> None:
    """Initializes global logging handlers (console + rotating file)."""
    if getattr(_init_logger_system, "_initialized", False):
        return  # already initialized

    # QUIET_STARTUP mode: suppress DEBUG logs, only show INFO+
    quiet_startup = os.getenv("QUIET_STARTUP", "0") == "1"
    log_level = logging.INFO if quiet_startup else (logging.DEBUG if DEBUG_MODE else logging.INFO)

    # Ensure logs directory exists
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "app.log")

    # Common formatter
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # File handler with rotation (always enabled)
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Root configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Close existing handlers to avoid unclosed file warnings
    for h in list(root_logger.handlers):
        try:
            h.close()
        except Exception:
            pass
    root_logger.handlers.clear()

    # Console handler - only in DEBUG trading mode (and not in quiet mode)
    if TRADING_MODE == "DEBUG" and not quiet_startup:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    # File handler always added
    root_logger.addHandler(file_handler)
    root_logger.propagate = False

    # Console notice - only in DEBUG mode and not quiet
    if TRADING_MODE == "DEBUG" and not quiet_startup:
        level_name = logging.getLevelName(log_level)
        print(f"[Logger] Initialized ({level_name}) → {log_path}")
        print("[Logger] Console output enabled (TRADING_MODE=DEBUG)")
    elif quiet_startup and TRADING_MODE == "DEBUG":
        print(f"[Logger] QUIET_STARTUP mode enabled → {log_path}")

    _init_logger_system._initialized = True


def get_logger(name: str = "APPSIERRA") -> logging.Logger:
    """
    Returns a module-scoped logger.
    Example:
        log = get_logger(__name__)
        log.info("Hello from module")
    """
    _init_logger_system()
    logger = logging.getLogger(name)
    return logger


def setup_debug_logging(enabled: bool = False) -> None:
    """
    Globally elevate log level to DEBUG if enabled=True.
    Useful for runtime toggles.
    """
    root = logging.getLogger()
    new_level = logging.DEBUG if enabled else logging.INFO
    root.setLevel(new_level)
    for h in root.handlers:
        h.setLevel(new_level)

    # Only print to console in DEBUG trading mode
    if TRADING_MODE == "DEBUG":
        print(f"[Logger] Runtime level set to {logging.getLevelName(new_level)}")


# -------------------- logger (end)
