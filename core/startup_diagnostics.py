# -------------------- core/startup_diagnostics.py (start)
"""
Module: core/startup_diagnostics.py
Purpose: Unified system health verification at APPSIERRA startup.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from utils.logger import get_logger


# -------------------- settings access (start)
try:
    from config import settings as _settings
except Exception:
    # Extremely defensive: allow diagnostics to run even if config import fails
    _settings = type("SettingsFallback", (), {})()  # type: ignore[misc]


def _cfg(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch a config value from config.settings; else environment; else default."""
    return getattr(_settings, name, os.getenv(name, default))


# -------------------- settings access (end)

# Canonical pulls
POSTGRES_DSN: Optional[str] = _cfg("POSTGRES_DSN", None)
DB_URL: Optional[str] = _cfg("DB_URL", None)  # legacy fallback
SNAPSHOT_CSV_PATH: Optional[str] = _cfg("SNAPSHOT_CSV_PATH", None)
DTC_HOST: Optional[str] = _cfg("DTC_HOST", None)
DTC_PORT: Optional[str] = _cfg("DTC_PORT", None)

# Soft-DTC toggles:
# - settings.SIM_ONLY = True  -> treat missing DTC as a warning, not a failure
# - env APPSIERRA_DIAG_ALLOW_NO_DTC=1 -> same effect without touching code/config
SIM_ONLY: bool = str(_cfg("SIM_ONLY", "0")).lower() in ("1", "true", "yes")
ALLOW_NO_DTC: bool = str(os.getenv("APPSIERRA_DIAG_ALLOW_NO_DTC", "0")).lower() in ("1", "true", "yes")

logger = get_logger("StartupDiagnostics")


# -------------------- individual checks (start)
def _db_probe_via_shared_layer() -> tuple[bool, str]:
    """
    Prefer the app's shared DB layer if available to avoid creating duplicate engines.
    Expects data.db_engine.health_check() -> (ok: bool, detail: str).
    """
    try:
        from data.db_engine import health_check  # type: ignore
    except Exception:
        return False, "Shared DB health_check not available"
    try:
        ok, detail = health_check()
        return bool(ok), str(detail)
    except Exception as e:
        return False, f"Shared-layer DB check error: {e}"


def _db_probe_direct() -> tuple[bool, str]:
    """
    Fallback: direct read-only probe using psycopg if DSN is configured.
    Sends 'SELECT 1' and closes immediately.
    """
    dsn = POSTGRES_DSN or DB_URL
    if not dsn:
        return False, "No DSN provided (POSTGRES_DSN/DB_URL unset)"

    # psycopg v3 import; guarded to avoid hard dependency
    try:
        import psycopg  # type: ignore
    except Exception as e:
        return False, f"psycopg not available for direct probe ({e})"

    try:
        # Low-cost connect; rely on server/connect timeout defaults
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True, "PostgreSQL 'SELECT 1' succeeded"
    except Exception as e:
        return False, f"Direct DB probe failed: {e}"


def check_database() -> tuple[bool, str]:
    """
    Verify DB connectivity.
    Strategy: shared-layer probe first; if absent, try direct psycopg probe.
    """
    ok, detail = _db_probe_via_shared_layer()
    if ok:
        return True, "PostgreSQL connected successfully"
    # Shared layer missing or failed; attempt direct probe (only if DSN exists)
    ok2, detail2 = _db_probe_direct()
    return (ok2, ("PostgreSQL connected successfully" if ok2 else f"Database connection failed: {detail2 or detail}"))


def check_snapshot_csv(max_age_sec: float = 5.0) -> tuple[bool, str, dict[str, Any]]:
    """
    Verify that the snapshot CSV file exists and report freshness.
    Returns (ok, message, extras).
    """
    path = SNAPSHOT_CSV_PATH or ""
    extras: dict[str, Any] = {"snapshot_csv_path": path}

    if not path:
        return False, "SNAPSHOT_CSV_PATH not set", extras

    p = Path(path)
    if not p.exists():
        return False, f"Snapshot CSV missing at {path}", extras

    try:
        mtime = p.stat().st_mtime
        age = max(0.0, datetime.now().timestamp() - mtime)
        extras["snapshot_csv_mtime"] = datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
        if age <= max_age_sec:
            return True, f"Snapshot CSV active (updated {age:.1f}s ago)", extras
        return True, f"Snapshot CSV stale (last update {age:.1f}s ago)", extras
    except OSError as e:
        return False, f"Failed to read CSV file: {e}", extras


def check_dtc_config() -> tuple[bool, str, str]:
    """
    Validate DTC configuration variables are present.
    Returns (ok, human_message, status_str) where status_str ∈ {"pending","error"} for summary row.
    """
    host_ok = bool(DTC_HOST)
    port_ok = bool(DTC_PORT)
    if host_ok and port_ok:
        return True, f"DTC config valid ({DTC_HOST}:{DTC_PORT})", "pending"

    if SIM_ONLY or ALLOW_NO_DTC:
        reason = "SIM_ONLY" if SIM_ONLY else "APPSIERRA_DIAG_ALLOW_NO_DTC"
        return False, f"DTC config incomplete — skipping in soft-DTC mode ({reason})", "pending"

    return False, "DTC config incomplete — missing host or port", "error"


# -------------------- individual checks (end)


# -------------------- orchestrator (start)
def run_diagnostics() -> dict[str, Any]:
    """
    Execute all diagnostic checks, print a compact 3-line summary,
    and log detailed results to app.log.

    Overall status is PASS when:
      - All checks pass, OR
      - The only failing check(s) are DTC config in soft-DTC mode.
    """
    results: dict[str, Any] = {}

    logger.info("──────────────────────────────────────────────")
    logger.info("🧭  APPSIERRA Startup Diagnostics")
    logger.info("──────────────────────────────────────────────")

    # Database
    db_ok, db_msg = check_database()
    # Snapshot CSV
    csv_ok, csv_msg, csv_extras = check_snapshot_csv()
    # DTC (config-stage status)
    dtc_ok, dtc_msg, dtc_status = check_dtc_config()

    # Console summary: exactly three lines
    print(f"[{'OK' if db_ok else 'FAIL'}] PostgreSQL connection")
    print(f"[{'OK' if csv_ok else 'FAIL'}] Snapshot CSV found")
    # If config incomplete but soft-allowed, still show "pending" with a cross
    dtc_line_ok = dtc_ok or (not dtc_ok and (SIM_ONLY or ALLOW_NO_DTC))
    print(f"[{'OK' if dtc_line_ok else 'FAIL'}] DTC connection pending")

    # Detailed logs
    (logger.info if db_ok else logger.warning)(f"DB: {db_msg}")
    (logger.info if csv_ok else logger.warning)(f"CSV: {csv_msg}")
    (logger.info if dtc_ok else logger.warning)(f"DTC: {dtc_msg}")

    # Overall computation
    hard_fail = not db_ok or not csv_ok
    dtc_fail = not dtc_ok
    soft_dtc = SIM_ONLY or ALLOW_NO_DTC
    overall_ok = (not hard_fail) and (not dtc_fail or soft_dtc)

    # Result payload
    results.update(
        {
            "postgres_ok": db_ok,
            "postgres_error": None if db_ok else db_msg,
            "snapshot_csv_ok": csv_ok,
            "dtc_status": dtc_status,
            "overall": overall_ok,
        }
    )
    results.update(csv_extras)

    logger.info("──────────────────────────────────────────────")
    if overall_ok:
        if dtc_fail and soft_dtc:
            logger.warning("DTC missing but allowed in soft-DTC mode — proceeding.")
        else:
            logger.info("All diagnostics passed successfully.")
    else:
        logger.warning("One or more diagnostics failed.")
    logger.info("──────────────────────────────────────────────")

    return results


# -------------------- orchestrator (end)


# -------------------- manual entrypoint (start)
if __name__ == "__main__":
    summary = run_diagnostics()
    print("\nDiagnostic summary object:")
    for key, val in summary.items():
        print(f"{key}: {val}")
# -------------------- manual entrypoint (end)
# -------------------- core/startup_diagnostics.py (end)
