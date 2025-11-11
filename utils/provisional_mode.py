"""
Provisional Boot Mode

Handles persistent storage of last known mode/account with 24h TTL.
UI boots in provisional mode until first DTC confirmation arrives.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_persistence import load_json_atomic, save_json_atomic
from utils.logger import get_logger

log = get_logger(__name__)

# TTL for last known mode (24 hours)
LAST_KNOWN_MODE_TTL_HOURS = 24

# Storage path
LAST_KNOWN_MODE_FILE = Path("data/last_known_mode.json")


def save_last_known_mode(mode: str, account: str) -> bool:
    """
    Save last known mode and account with timestamp.

    Args:
        mode: Trading mode ("LIVE", "SIM", "DEBUG")
        account: Account identifier

    Returns:
        True if saved successfully

    Example:
        save_last_known_mode("SIM", "Sim1")
    """
    try:
        data = {
            "mode": mode,
            "account": account,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ttl_hours": LAST_KNOWN_MODE_TTL_HOURS,
        }

        success = save_json_atomic(data, LAST_KNOWN_MODE_FILE)
        if success:
            log.debug(f"[ProvisionalMode] Saved last known mode: {mode}, account: {account}")
        return success

    except Exception as e:
        log.error(f"[ProvisionalMode] Error saving last known mode: {e}")
        return False


def load_last_known_mode() -> Optional[tuple[str, str]]:
    """
    Load last known mode and account if within TTL.

    Returns:
        Tuple of (mode, account) if valid, None if expired or not found

    Example:
        result = load_last_known_mode()
        if result:
            mode, account = result
            # Boot in provisional mode
        else:
            # No valid last known mode
    """
    try:
        data = load_json_atomic(LAST_KNOWN_MODE_FILE)
        if not data:
            log.debug("[ProvisionalMode] No last known mode file found")
            return None

        mode = data.get("mode")
        account = data.get("account")
        timestamp_str = data.get("timestamp_utc")
        ttl_hours = data.get("ttl_hours", LAST_KNOWN_MODE_TTL_HOURS)

        if not all([mode, account, timestamp_str]):
            log.warning("[ProvisionalMode] Invalid last known mode data (missing fields)")
            return None

        # Parse timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            # Assume UTC if no timezone
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Check TTL
        now = datetime.now(timezone.utc)
        age = now - timestamp
        max_age = timedelta(hours=ttl_hours)

        if age > max_age:
            log.info(f"[ProvisionalMode] Last known mode expired (age: {age}, max: {max_age})")
            return None

        log.info(f"[ProvisionalMode] Loaded last known mode: {mode}, account: {account} (age: {age})")
        return (mode, account)

    except Exception as e:
        log.error(f"[ProvisionalMode] Error loading last known mode: {e}")
        return None


def is_provisional_mode_valid() -> bool:
    """
    Check if last known mode is still valid (within TTL).

    Returns:
        True if valid provisional mode exists
    """
    return load_last_known_mode() is not None


def get_provisional_mode_status() -> dict[str, any]:
    """
    Get detailed status of provisional mode.

    Returns:
        Dictionary with status info:
        - valid: bool - Whether provisional mode is valid
        - mode: str | None - Last known mode
        - account: str | None - Last known account
        - age_seconds: float | None - Age in seconds
        - ttl_seconds: float - TTL in seconds

    Example:
        status = get_provisional_mode_status()
        if status["valid"]:
            print(f"Boot in provisional mode: {status['mode']}")
    """
    result = load_last_known_mode()

    if result:
        mode, account = result
        # Calculate age
        data = load_json_atomic(LAST_KNOWN_MODE_FILE)
        timestamp = datetime.fromisoformat(data["timestamp_utc"].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()

        return {
            "valid": True,
            "mode": mode,
            "account": account,
            "age_seconds": age,
            "ttl_seconds": LAST_KNOWN_MODE_TTL_HOURS * 3600,
        }
    else:
        return {
            "valid": False,
            "mode": None,
            "account": None,
            "age_seconds": None,
            "ttl_seconds": LAST_KNOWN_MODE_TTL_HOURS * 3600,
        }
