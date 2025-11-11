"""
services/market_data_service.py

Market data feed service - handles CSV snapshot reading and market data parsing.

This service provides:
- CSV snapshot reading (last, high, low, vwap, cum_delta, poc)
- BOM-aware parsing
- Robust column ordering and error handling
- Centralized market data access
"""

from __future__ import annotations

import csv
import os
from typing import Optional
from dataclasses import dataclass

from utils.logger import get_logger


log = get_logger(__name__)


@dataclass
class MarketSnapshot:
    """Market snapshot data structure"""
    last_price: float = 0.0
    session_high: float = 0.0
    session_low: float = 0.0
    vwap: float = 0.0
    cum_delta: float = 0.0
    poc: float = 0.0


class MarketDataService:
    """
    Market data feed service.

    Reads CSV snapshots and provides market data to panels.
    Thread-safe, BOM-aware, robust to missing columns.
    """

    def __init__(self, csv_path: str):
        """
        Initialize market data service.

        Args:
            csv_path: Path to CSV snapshot file
        """
        self.csv_path = csv_path
        self._missing_csv_logged = False

    def read_snapshot(self) -> Optional[MarketSnapshot]:
        """
        Read current market snapshot from CSV.

        Returns:
            MarketSnapshot if successful, None if file not found or error

        CSV Format:
            Header row: last,high,low,vwap,cum_delta,poc
            Data row: float values
        """
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                row = next(reader, None)  # first data row after header
                if not row:
                    return None

                def fnum(key: str) -> float:
                    """Extract float from CSV cell, default to 0.0 on error"""
                    val = (row.get(key, "") or "").strip()
                    if not val:
                        return 0.0
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                return MarketSnapshot(
                    last_price=fnum("last"),
                    session_high=fnum("high"),
                    session_low=fnum("low"),
                    vwap=fnum("vwap"),
                    cum_delta=fnum("cum_delta"),
                    poc=fnum("poc"),
                )

        except FileNotFoundError:
            if not self._missing_csv_logged:
                log.warning(f"[market_data_service] Snapshot CSV not found at: {self.csv_path}")
                self._missing_csv_logged = True
            return None
        except StopIteration:
            # Header exists but no data rows yet
            return None
        except Exception as e:
            log.error(f"[market_data_service] CSV read error: {e}")
            return None

    def get_last_price(self) -> Optional[float]:
        """Quick accessor for last price only"""
        snapshot = self.read_snapshot()
        return snapshot.last_price if snapshot else None

    def get_vwap(self) -> Optional[float]:
        """Quick accessor for VWAP only"""
        snapshot = self.read_snapshot()
        return snapshot.vwap if snapshot else None

    def get_session_range(self) -> tuple[Optional[float], Optional[float]]:
        """Get session high and low as tuple"""
        snapshot = self.read_snapshot()
        if snapshot:
            return snapshot.session_high, snapshot.session_low
        return None, None
