"""
services/dtc_ledger.py

Python port of PowerShell dtc_build_ledgers.ps1
Builds order ledgers, snapshots, and fill streams from DTC Type 301 messages.

This provides sophisticated order state tracking:
- Groups Type 301 messages by ServerOrderID
- Finds terminal status (Filled/Canceled/Rejected prioritized)
- Tracks High/Low during position
- Detects exit kind (Stop/Limit/Market)
- Builds 3 reports: OrderLedger, LatestSnapshot, FillStream
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional

from services.dtc_schemas import OrderUpdate, parse_dtc_message
from utils.logger import get_logger


log = get_logger(__name__)


# ==================== Terminal Status Priority ====================

# Higher rank = more final (Filled/Rejected/Canceled > PartiallyFilled > Open > New)
TERMINAL_RANK = {
    7: 5,  # Filled
    8: 5,  # Rejected
    6: 5,  # Canceled
    9: 4,  # PartiallyFilled
    4: 3,  # Open
    2: 2,  # Submitted
    1: 1,  # New
    3: 1,  # PendingCancel
    5: 1,  # PendingReplace
}


# ==================== Data Classes ====================


@dataclass
class OrderLedgerEntry:
    """Terminal state summary for one order (grouped by ServerOrderID)"""

    server_order_id: str
    symbol: Optional[str] = None
    trade_account: Optional[str] = None
    side: Optional[str] = None  # "Buy" or "Sell"
    order_type: Optional[str] = None  # "Market", "Limit", "Stop", "StopLimit"
    qty: Optional[float] = None
    price: Optional[float] = None
    filled_qty: Optional[float] = None
    avg_fill_price: Optional[float] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    exit_kind: Optional[str] = None  # "Stop", "Limit", "Market" (only on fills)
    high_during_pos: Optional[float] = None
    low_during_pos: Optional[float] = None
    first_time: Optional[float] = None
    last_time: Optional[float] = None
    duration_sec: Optional[float] = None
    text: Optional[str] = None


@dataclass
class OrderSnapshot:
    """Latest state for one order"""

    server_order_id: str
    symbol: Optional[str] = None
    trade_account: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    qty: Optional[float] = None
    price: Optional[float] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    text: Optional[str] = None


@dataclass
class FillEntry:
    """Single fill event"""

    time: Optional[float] = None
    server_order_id: Optional[str] = None
    symbol: Optional[str] = None
    trade_account: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    last_fill_qty: Optional[float] = None
    last_fill_price: Optional[float] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    text: Optional[str] = None


# ==================== JSONL Reader ====================


def read_dtc_jsonl(path: str) -> list[OrderUpdate]:
    """
    Read DTC Type 301 (OrderUpdate) messages from JSONL file.

    Args:
        path: Path to JSONL file

    Returns:
        List of parsed OrderUpdate objects
    """
    updates = []
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    with open(path_obj, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
                if raw.get("Type") == 301 and raw.get("ServerOrderID"):
                    msg = parse_dtc_message(raw)
                    if isinstance(msg, OrderUpdate):
                        updates.append(msg)
            except json.JSONDecodeError as e:
                log.warning(f"Line {line_num}: Invalid JSON - {e}")
            except Exception as e:
                log.warning(f"Line {line_num}: Parse error - {e}")

    return updates


# ==================== Ledger Builder ====================


class OrderLedgerBuilder:
    """Builds order ledgers from DTC OrderUpdate messages"""

    def __init__(self, updates: list[OrderUpdate]):
        self.updates = updates
        self.grouped: dict[str, list[OrderUpdate]] = defaultdict(list)
        self._group_by_server_order_id()

    def _group_by_server_order_id(self):
        """Group all updates by ServerOrderID"""
        for upd in self.updates:
            if upd.ServerOrderID:
                self.grouped[upd.ServerOrderID].append(upd)

    def _get_terminal_rank(self, upd: OrderUpdate) -> int:
        """Get terminal priority rank for an order status"""
        return TERMINAL_RANK.get(upd.OrderStatus or 0, 0)

    def _find_best_update(self, updates: list[OrderUpdate]) -> OrderUpdate:
        """
        Find the "best" (most terminal) update for a group.
        Priority: highest terminal rank, then latest timestamp.
        """
        return max(updates, key=lambda u: (self._get_terminal_rank(u), u.get_timestamp() or 0))

    def _find_first_update(self, updates: list[OrderUpdate]) -> OrderUpdate:
        """Find the earliest update by timestamp"""
        return min(updates, key=lambda u: u.get_timestamp() or 0)

    def _find_last_update(self, updates: list[OrderUpdate]) -> OrderUpdate:
        """Find the latest update by timestamp"""
        return max(updates, key=lambda u: u.get_timestamp() or 0)

    def _max_filled_qty(self, updates: list[OrderUpdate]) -> Optional[float]:
        """Get maximum FilledQuantity across all updates"""
        filled = [u.FilledQuantity for u in updates if u.FilledQuantity is not None]
        return max(filled) if filled else None

    def _detect_exit_kind(self, upd: OrderUpdate) -> Optional[str]:
        """
        Detect exit type based on OrderType and status.
        Only label on terminal fills.
        """
        if not upd.is_terminal():
            return None

        if upd.OrderStatus != 7:  # Not filled
            return None

        type_map = {
            3: "Stop",
            2: "Limit",
            1: "Market",
            4: "StopLimit",
        }
        return type_map.get(upd.OrderType)

    def build_ledger(self) -> list[OrderLedgerEntry]:
        """
        Build order ledger summary (terminal state for each order).

        Returns:
            List of OrderLedgerEntry objects
        """
        ledger = []

        for server_order_id, updates in self.grouped.items():
            if not updates:
                continue

            best = self._find_best_update(updates)
            first = self._find_first_update(updates)
            last = self._find_last_update(updates)

            t0 = first.get_timestamp() or 0
            t1 = last.get_timestamp() or t0
            duration = round(t1 - t0, 3) if (t1 and t0) else None

            entry = OrderLedgerEntry(
                server_order_id=server_order_id,
                symbol=best.Symbol,
                trade_account=best.TradeAccount,
                side=best.get_side(),
                order_type=best.get_order_type(),
                qty=best.get_quantity(),
                price=best.get_price(),
                filled_qty=self._max_filled_qty(updates),
                avg_fill_price=best.get_avg_fill_price(),
                status=best.get_status(),
                reason=best.get_reason(),
                exit_kind=self._detect_exit_kind(best),
                high_during_pos=best.get_high_during_position(),
                low_during_pos=best.get_low_during_position(),
                first_time=t0,
                last_time=t1,
                duration_sec=duration,
                text=best.get_text(),
            )

            ledger.append(entry)

        return ledger

    def build_snapshot(self) -> list[OrderSnapshot]:
        """
        Build latest snapshot (most recent update for each order).

        Returns:
            List of OrderSnapshot objects
        """
        snapshot = []

        for server_order_id, updates in self.grouped.items():
            if not updates:
                continue

            last = self._find_last_update(updates)

            snap = OrderSnapshot(
                server_order_id=server_order_id,
                symbol=last.Symbol,
                trade_account=last.TradeAccount,
                side=last.get_side(),
                order_type=last.get_order_type(),
                qty=last.get_quantity(),
                price=last.get_price(),
                status=last.get_status(),
                reason=last.get_reason(),
                text=last.get_text(),
            )

            snapshot.append(snap)

        return snapshot

    def build_fill_stream(self) -> list[FillEntry]:
        """
        Build chronological fill stream (all fill events).

        Returns:
            List of FillEntry objects sorted by timestamp
        """
        fills = []

        for upd in self.updates:
            # Include updates that are fill-related
            if upd.is_fill_update():
                fill = FillEntry(
                    time=upd.LastFillDateTime or upd.get_timestamp(),
                    server_order_id=upd.ServerOrderID,
                    symbol=upd.Symbol,
                    trade_account=upd.TradeAccount,
                    side=upd.get_side(),
                    order_type=upd.get_order_type(),
                    last_fill_qty=upd.LastFillQuantity or upd.FilledQuantity or 1,
                    last_fill_price=(upd.LastFillPrice or upd.get_avg_fill_price() or upd.get_price()),
                    status=upd.get_status(),
                    reason=upd.get_reason(),
                    text=upd.get_text(),
                )
                fills.append(fill)

        # Sort by timestamp
        fills.sort(key=lambda f: f.time or 0)

        return fills


# ==================== Export Utilities ====================


def export_to_csv(entries: list, output_path: str):
    """
    Export dataclass list to CSV.

    Args:
        entries: List of dataclass objects
        output_path: Path to output CSV file
    """
    import csv

    if not entries:
        log.warning(f"No entries to export to {output_path}")
        return

    path_obj = Path(output_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w", newline="", encoding="utf-8") as f:
        # Get fieldnames from first entry
        fieldnames = list(asdict(entries[0]).keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for entry in entries:
            writer.writerow(asdict(entry))

    log.info(f"Wrote {len(entries)} entries to {output_path}")


def export_to_json(entries: list, output_path: str, compact: bool = True):
    """
    Export dataclass list to JSON.

    Args:
        entries: List of dataclass objects
        output_path: Path to output JSON file
        compact: If True, use compact separators
    """
    path_obj = Path(output_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(entry) for entry in entries]

    with open(path_obj, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)

    log.info(f"Wrote {len(entries)} entries to {output_path}")
