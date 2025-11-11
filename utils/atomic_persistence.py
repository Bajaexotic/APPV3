"""
Atomic Persistence Utilities

Provides atomic file write operations to prevent data corruption.
All writes use temp-file → rename pattern for atomicity.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from utils.logger import get_logger

log = get_logger(__name__)

# Schema version for all persistence files
SCHEMA_VERSION = "2.0"


def save_json_atomic(data: dict[str, Any], file_path: Path | str, schema_version: Optional[str] = None) -> bool:
    """
    Save JSON data atomically using temp-file → rename pattern.

    Args:
        data: Dictionary to save
        file_path: Target file path
        schema_version: Schema version (defaults to SCHEMA_VERSION)

    Returns:
        True if successful, False otherwise

    Example:
        data = {"balance": 10000.0, "trades": 5}
        save_json_atomic(data, Path("data/state.json"))
    """
    try:
        file_path = Path(file_path)

        # Add metadata
        data["_schema_version"] = schema_version or SCHEMA_VERSION
        data["_saved_at_utc"] = datetime.now(timezone.utc).isoformat()

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Atomic rename (POSIX guarantees atomicity)
        temp_path.replace(file_path)

        log.debug(f"[AtomicPersist] Saved {file_path}")
        return True

    except Exception as e:
        log.error(f"[AtomicPersist] Error saving {file_path}: {e}")
        return False


def load_json_atomic(file_path: Path | str, expected_schema: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Load JSON data with schema validation.

    Args:
        file_path: Source file path
        expected_schema: Expected schema version (defaults to SCHEMA_VERSION)

    Returns:
        Loaded dictionary, or None if file doesn't exist or is invalid

    Example:
        data = load_json_atomic(Path("data/state.json"))
        if data:
            balance = data.get("balance", 0.0)
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            log.debug(f"[AtomicPersist] File not found: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate schema version
        schema = data.get("_schema_version")
        expected = expected_schema or SCHEMA_VERSION

        if schema != expected:
            log.warning(f"[AtomicPersist] Schema mismatch in {file_path}: got {schema}, expected {expected}")
            # Allow loading but warn about version mismatch
            # Don't return None - let caller decide how to handle

        log.debug(f"[AtomicPersist] Loaded {file_path}")
        return data

    except json.JSONDecodeError as e:
        log.error(f"[AtomicPersist] JSON decode error in {file_path}: {e}")
        return None
    except Exception as e:
        log.error(f"[AtomicPersist] Error loading {file_path}: {e}")
        return None


def delete_file_safe(file_path: Path | str) -> bool:
    """
    Safely delete a file (no error if doesn't exist).

    Args:
        file_path: File to delete

    Returns:
        True if deleted or didn't exist, False on error
    """
    try:
        file_path = Path(file_path)
        if file_path.exists():
            file_path.unlink()
            log.debug(f"[AtomicPersist] Deleted {file_path}")
        return True
    except Exception as e:
        log.error(f"[AtomicPersist] Error deleting {file_path}: {e}")
        return False


def get_scoped_path(base_name: str, mode: str, account: str, extension: str = ".json") -> Path:
    """
    Generate a (mode, account)-scoped file path.

    Args:
        base_name: Base filename (e.g., "panel2_state")
        mode: Trading mode ("SIM", "LIVE", "DEBUG")
        account: Account identifier (e.g., "Sim1", "120005")
        extension: File extension (default: ".json")

    Returns:
        Scoped path: data/{base_name}_{mode}_{account}.json

    Example:
        path = get_scoped_path("panel2_state", "SIM", "Sim1")
        # Returns: data/panel2_state_SIM_Sim1.json
    """
    # Sanitize account for filename (remove special chars)
    account_safe = "".join(c if c.isalnum() else "_" for c in account)
    filename = f"{base_name}_{mode}_{account_safe}{extension}"
    return Path("data") / filename


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO 8601 format.

    Returns:
        ISO 8601 timestamp with 'Z' suffix

    Example:
        timestamp = get_utc_timestamp()
        # Returns: "2025-11-11T14:23:45.123456Z"
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_schema(data: dict[str, Any], expected_version: str = SCHEMA_VERSION) -> bool:
    """
    Validate schema version of loaded data.

    Args:
        data: Loaded dictionary
        expected_version: Expected schema version

    Returns:
        True if schema matches, False otherwise
    """
    schema = data.get("_schema_version")
    return schema == expected_version
