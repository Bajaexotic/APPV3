from __future__ import annotations

from typing import Any, Dict, Optional


def load_open_position() -> Optional[dict[str, Any]]:
    """
    DEPRECATED: PositionRecord no longer exists in schema.
    Position tracking is inferred from OrderRecord execution, not from DTC Type 306 messages.

    Sierra Chart does NOT send unsolicited Type 306 PositionUpdate messages.
    All position state must come from LIVE DTC events, not database persistence.

    Returns None to force live-only position tracking.
    """
    return None
