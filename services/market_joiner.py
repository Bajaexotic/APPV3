# -------------------- market_joiner (start)
"""
services/market_joiner.py
Bridges Sierra Chart's CSV snapshot feed (Last, High, Low, Vwap, CumDelta)
into APPSIERRA's live trading context. Reads lightweight CSV snapshot and
merges those metrics into DTC or DB-derived symbol data.
"""

from __future__ import annotations

import csv
import os
import time
from typing import Any, Dict, Optional

from config.settings import SNAPSHOT_CSV_PATH
from utils.logger import get_logger


log = get_logger(__name__)


class MarketJoiner:
    """Lightweight bridge between snapshot.csv and live DTC/DB context."""

    def __init__(self, csv_path: Optional[str] = None) -> None:
        self._csv_path = csv_path or SNAPSHOT_CSV_PATH
        self._cache: dict[str, float] = {}
        self._last_read_time: float = 0.0
        self._last_mtime: float = 0.0

    # ------------------------------------------------------------------
    def read_snapshot(self) -> dict[str, float]:
        """
        Reads the latest market metrics from the snapshot CSV.
        Expected header: last,high,low,vwap,cum_delta
        Returns parsed floats; falls back to cached values if read fails.
        """
        try:
            if not os.path.exists(self._csv_path):
                log.warning(f"Snapshot file not found: {self._csv_path}")
                return self._cache

            mtime = os.path.getmtime(self._csv_path)
            if mtime == self._last_mtime:
                # file unchanged; reuse cache
                return self._cache

            with open(self._csv_path, newline="") as f:
                reader = csv.DictReader(f)
                last_row = None
                for row in reader:
                    last_row = row

            if not last_row:
                log.warning("Snapshot file empty or invalid.")
                return self._cache

            # Parse numeric values safely
            parsed = {}
            for key in ("last", "high", "low", "vwap", "cum_delta"):
                try:
                    parsed[key] = float(last_row[key])
                except (KeyError, ValueError, TypeError):
                    parsed[key] = self._cache.get(key, 0.0)
                    log.debug(f"Snapshot parse fallback for key: {key}")

            self._cache = parsed
            self._last_read_time = time.time()
            self._last_mtime = mtime
            log.debug(f"Snapshot updated: {parsed}")
            return parsed

        except Exception as e:
            log.warning(f"Snapshot read failed: {e}")
            return self._cache

    # ------------------------------------------------------------------
    def get_last_snapshot(self) -> dict[str, float]:
        """Returns cached snapshot without rereading the file."""
        return self._cache

    # ------------------------------------------------------------------
    def merge_context(self, symbol_data: dict[str, Any]) -> dict[str, Any]:
        """
        Merges current snapshot metrics into an existing symbol record.
        Input: dict containing at least 'symbol' key from DTC or DB record.
        Output: enriched dict with Last/High/Low/VWAP/CumDelta.
        """
        snapshot = self.read_snapshot()
        enriched = dict(symbol_data)
        enriched.update(snapshot)
        return enriched


# ----------------------------------------------------------------------
# Utility singleton for global access
_market_joiner: Optional[MarketJoiner] = None


def get_market_joiner() -> MarketJoiner:
    """Returns a shared MarketJoiner instance (singleton pattern)."""
    global _market_joiner
    if _market_joiner is None:
        _market_joiner = MarketJoiner()
    return _market_joiner


# -------------------- market_joiner (end)
