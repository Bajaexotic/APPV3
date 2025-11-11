# -------------------- config/settings.py (start)
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


# --- Paths ---
HOME: str = str(Path.home())
APP_ROOT: Path = Path(HOME)  # kept generic; app may override via sys.path logic
CACHE_DIR: str = str(Path(HOME) / ".sierra_pnl_monitor")
CACHE_FILE: str = str(Path(CACHE_DIR) / "equity_timeseries.jsonl")

# Logs directory (used by utils/logger.py)
LOG_DIR: str = str(Path(APP_ROOT) / "Desktop" / "APPSIERRA" / "logs")

# Ensure cache/log dirs exist (non-fatal)
for _p in (CACHE_DIR, LOG_DIR):
    with contextlib.suppress(Exception):
        Path(_p).mkdir(parents=True, exist_ok=True)

# --- Feature flags ---
ENABLE_CONFIG_JSON: bool = True  # use ~/.sierra_pnl_monitor/config.json to override select keys
DEBUG_MODE: bool = bool(int(os.getenv("DEBUG_MODE", "0")))
DEBUG_DTC: bool = bool(int(os.getenv("DEBUG_DTC", "0")))

# Advanced debug subsystem flags (independent toggles)
DEBUG_CORE: bool = bool(int(os.getenv("DEBUG_CORE", "0")))  # Core systems (app_manager, state_manager)
DEBUG_UI: bool = bool(int(os.getenv("DEBUG_UI", "0")))  # UI render events, signals, widgets
DEBUG_DATA: bool = bool(int(os.getenv("DEBUG_DATA", "0")))  # DTC/JSON payloads, schema, cache
DEBUG_NETWORK: bool = bool(int(os.getenv("DEBUG_NETWORK", "0")))  # Socket connectivity, heartbeats
DEBUG_ANALYTICS: bool = bool(int(os.getenv("DEBUG_ANALYTICS", "0")))  # Metrics, performance calculations
DEBUG_PERF: bool = bool(int(os.getenv("DEBUG_PERF", "0")))  # Latency, CPU, memory measurements

# Trading mode selection (DEBUG/LIVE/SIM)
# Can be set via: environment variable, config.json, or command-line arg
# Eventually will be auto-detected from DTC LogonResponse message
TRADING_MODE: str = os.getenv("TRADING_MODE", "SIM").upper()  # Default to SIM for safety


# -------------------- helpers --------------------
def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val not in ("", None) else default


def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    val = os.getenv(name)
    if val in (None, ""):
        return default
    try:
        return int(val)
    except Exception:
        return default


def _env_float(name: str, default: Optional[float] = None) -> Optional[float]:
    val = os.getenv(name)
    if val in (None, ""):
        return default
    try:
        return float(val)
    except Exception:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, "1" if default else "0")).strip().lower() in ("1", "true", "yes", "on")


def _mask_secret(s: Optional[str], keep: int = 6) -> str:
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "…" + "*" * 4


# -------------------- JSON override loader (start)
APP_CONFIG_JSON_PATH: Path = Path(r"C:\Users\cgrah\Desktop\APPSIERRA\config\config.json")
CONFIG_JSON_PATH: Path = APP_CONFIG_JSON_PATH


def _load_config_json() -> dict[str, Any]:
    """Load app-local override JSON if present; return {} on any issue."""
    if not ENABLE_CONFIG_JSON:
        return {}
    try:
        with APP_CONFIG_JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


# -------------------- JSON override loader (end)
# -------------------- DTC / Sierra connection --------------------
# Verified: 127.0.0.1:11099 is common local gateway
DTC_HOST: str = _env_str("SIERRA_DTC_HOST", "127.0.0.1") or "127.0.0.1"
DTC_PORT: int = _env_int("SIERRA_DTC_PORT", 11099) or 11099

# Optional auth
DTC_USERNAME: Optional[str] = _env_str("SIERRA_DTC_USER", None)
DTC_PASSWORD: Optional[str] = _env_str("SIERRA_DTC_PASS", None)

# Trading context
LIVE_ACCOUNT: str = _env_str("SIERRA_TRADE_ACCOUNT", "120005") or "120005"
SYMBOL_BASE: str = _env_str("SIERRA_SYMBOL_BASE", "ES") or "ES"

# -------------------- Time windows (seconds) --------------------
LIVE_WINDOW_SEC: int = _env_int("LIVE_WINDOW_SEC", 60 * 60) or 60 * 60  # 1 hour
WEEK_WINDOW_SEC: int = _env_int("WEEK_WINDOW_SEC", 7 * 24 * 60 * 60) or 7 * 24 * 60 * 60
MONTH_WINDOW_SEC: int = _env_int("MONTH_WINDOW_SEC", 30 * 24 * 60 * 60) or 30 * 24 * 60 * 60
QUARTER_WINDOW_SEC: int = _env_int("QUARTER_WINDOW_SEC", 90 * 24 * 60 * 60) or 90 * 24 * 60 * 60
RIGHT_PAD_SEC: float = _env_float("RIGHT_PAD_SEC", 50.0) or 50.0

# -------------------- Rendering / visual parameters --------------------
Y_TOP_HEADROOM: float = _env_float("Y_TOP_HEADROOM", 0.25) or 0.25
Y_BOTTOM_GAP: float = _env_float("Y_BOTTOM_GAP", 0.40) or 0.40
ENABLE_GLOW: bool = _env_bool("ENABLE_GLOW", True)
GLOW_WIDTH_MULT: float = _env_float("GLOW_WIDTH_MULT", 2.8) or 2.8
GLOW_OPACITY: float = _env_float("GLOW_OPACITY", 0.22) or 0.22
ENABLE_TRAIL_FADE: bool = _env_bool("ENABLE_TRAIL_FADE", True)
TRAIL_TAIL_SECONDS: float = _env_float("TRAIL_TAIL_SECONDS", 25.0) or 25.0
HISTORY_OPACITY: float = _env_float("HISTORY_OPACITY", 0.66) or 0.66
SMOOTH_EMA_ALPHA: float = _env_float("SMOOTH_EMA_ALPHA", 0.18) or 0.18

# -------------------- Timeframe configuration (always defined) --------------------
TF_CONFIGS: dict[str, dict[str, Any]] = {
    "LIVE": {"snap_sec": 15, "window_sec": LIVE_WINDOW_SEC},
    "1D": {"snap_sec": 300, "window_sec": None},
    "1W": {"snap_sec": 1800, "window_sec": WEEK_WINDOW_SEC},
    "1M": {"snap_sec": 86400, "window_sec": MONTH_WINDOW_SEC},
    "3M": {"snap_sec": 86400, "window_sec": QUARTER_WINDOW_SEC},
    "YTD": {"snap_sec": 86400, "window_sec": None},
}

# -------------------- Database configuration --------------------
# Preferred: single DSN via POSTGRES_DSN (e.g., postgresql+psycopg://user:pass@host:5432/dbname)
POSTGRES_DSN: Optional[str] = _env_str("POSTGRES_DSN", None)

# Backward compatibility: accept discrete envs to construct DSN only if ALL are present
_pg_host = _env_str("PG_HOST", None)
_pg_port = _env_int("PG_PORT", None)
_pg_user = _env_str("PG_USER", None)
_pg_pass = _env_str("PG_PASSWORD", None)
_pg_db = _env_str("PG_DATABASE", None)

if not POSTGRES_DSN and all([_pg_host, _pg_port, _pg_user, _pg_pass, _pg_db]):
    POSTGRES_DSN = f"postgresql+psycopg://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

# Apply JSON overrides (JSON wins over env if key exists)
_config = _load_config_json()
if isinstance(_config, dict):
    if "POSTGRES_DSN" in _config and isinstance(_config["POSTGRES_DSN"], str) and _config["POSTGRES_DSN"].strip():
        POSTGRES_DSN = _config["POSTGRES_DSN"].strip()

    # Allow TRADING_MODE override from config.json
    if "TRADING_MODE" in _config and isinstance(_config["TRADING_MODE"], str):
        TRADING_MODE = _config["TRADING_MODE"].strip().upper()

# -------------------- Smart Database URL Configuration (START) --------------------
# Implements fallback chain: explicit DB_URL → POSTGRES_DSN → SQLite local
# This ensures trades are always persisted, even without external database

DB_URL: Optional[str] = _env_str("DB_URL", None)

# Fallback logic: use available database configuration in priority order
if not DB_URL:
    # Try PostgreSQL first (production/remote database)
    if POSTGRES_DSN:
        DB_URL = POSTGRES_DSN
    else:
        # Fall back to local SQLite (development/offline mode)
        # SQLite file location: data/appsierra.db
        _sqlite_path = Path(APP_ROOT) / "Desktop" / "APPSIERRA" / "data" / "appsierra.db"
        DB_URL = f"sqlite:///{str(_sqlite_path).replace(chr(92), '/')}"  # Convert backslashes for SQLite

# Ensure DB_URL is always set
if not DB_URL:
    # Last resort: in-memory SQLite (data lost on restart, but app won't crash)
    DB_URL = "sqlite:///:memory:"

# Log which database is being used (DEBUG mode only)
if DEBUG_MODE and TRADING_MODE == "DEBUG":
    if "postgresql" in (DB_URL or "").lower():
        print(f"[DB] Using PostgreSQL: {_mask_secret(DB_URL, 4)}")
    elif "sqlite" in (DB_URL or "").lower():
        print(f"[DB] Using SQLite: {DB_URL}")
    else:
        print(f"[DB] Using fallback database: {DB_URL}")

# -------------------- Smart Database URL Configuration (END) --------------------

# -------------------- Market Snapshot Feed --------------------
# Preferred alias name
SNAPSHOT_CSV_PATH: str = str(
    Path(
        _env_str("SNAPSHOT_CSV_PATH")
        or _env_str("CSV_MARKET_FEED_PATH")
        or f"C:/Users/{os.getenv('USERNAME', 'user')}/Desktop/APPSIERRA/data/snapshot.csv"
    )
)

# Optional boot banner (helps confirm effective values during dev without leaking secrets)
# Only show in DEBUG trading mode to keep LIVE/SIM terminal clean
if DEBUG_MODE and TRADING_MODE == "DEBUG":
    _dsn_echo = _mask_secret(POSTGRES_DSN)
    _debug_flags = (
        " | ".join(
            [
                f"DEBUG_{flag}={int(val)}"
                for flag, val in [
                    ("DTC", DEBUG_DTC),
                    ("CORE", DEBUG_CORE),
                    ("UI", DEBUG_UI),
                    ("DATA", DEBUG_DATA),
                    ("NETWORK", DEBUG_NETWORK),
                    ("ANALYTICS", DEBUG_ANALYTICS),
                    ("PERF", DEBUG_PERF),
                ]
                if val
            ]
        )
        or "none"
    )

    print(
        "[SETTINGS] "
        f"MODE={TRADING_MODE} | "
        f"DTC={DTC_HOST}:{DTC_PORT} | "
        f"LIVE_ACCOUNT={LIVE_ACCOUNT} | SYMBOL_BASE={SYMBOL_BASE} | "
        f"POSTGRES_DSN={_dsn_echo} | "
        f"SNAPSHOT_CSV_PATH={SNAPSHOT_CSV_PATH} | "
        f"LOG_DIR={LOG_DIR} | "
        f"DEBUG_FLAGS=[{_debug_flags}] | "
        f"CONFIG_JSON={'present' if _config else 'absent'}"
    )

# Explicit export list (useful for linters)
__all__ = [
    # Paths / flags
    "HOME",
    "APP_ROOT",
    "CACHE_DIR",
    "CACHE_FILE",
    "LOG_DIR",
    "ENABLE_CONFIG_JSON",
    "DEBUG_MODE",
    "DEBUG_DTC",
    # Advanced debug flags
    "DEBUG_CORE",
    "DEBUG_UI",
    "DEBUG_DATA",
    "DEBUG_NETWORK",
    "DEBUG_ANALYTICS",
    "DEBUG_PERF",
    # Trading mode
    "TRADING_MODE",
    # DTC
    "DTC_HOST",
    "DTC_PORT",
    "DTC_USERNAME",
    "DTC_PASSWORD",
    # Trading
    "LIVE_ACCOUNT",
    "SYMBOL_BASE",
    # Windows and visuals
    "LIVE_WINDOW_SEC",
    "WEEK_WINDOW_SEC",
    "MONTH_WINDOW_SEC",
    "QUARTER_WINDOW_SEC",
    "RIGHT_PAD_SEC",
    "Y_TOP_HEADROOM",
    "Y_BOTTOM_GAP",
    "ENABLE_GLOW",
    "GLOW_WIDTH_MULT",
    "GLOW_OPACITY",
    "ENABLE_TRAIL_FADE",
    "TRAIL_TAIL_SECONDS",
    "HISTORY_OPACITY",
    "SMOOTH_EMA_ALPHA",
    # TFs
    "TF_CONFIGS",
    # Data sources
    "POSTGRES_DSN",
    "DB_URL",
    "SNAPSHOT_CSV_PATH",
    "CONFIG_JSON_PATH",
]
# -------------------- config/settings.py (end)
