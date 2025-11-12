from __future__ import annotations

import csv
from datetime import UTC, datetime, timezone
import json
import os
import time
from typing import List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets

from config.theme import THEME, ColorTheme
from services.dtc_schemas import OrderUpdate, PositionUpdate, parse_dtc_message
from services.trade_constants import COMM_PER_CONTRACT, DOLLARS_PER_POINT
from utils.logger import get_logger
from utils.theme_mixin import ThemeAwareMixin
from widgets.metric_cell import MetricCell


log = get_logger(__name__)

# -------------------- Constants & Config (start)
CSV_FEED_PATH = r"C:\Users\cgrah\Desktop\APPSIERRA\data\snapshot.csv"
# STATE_PATH removed - now dynamically scoped by (mode, account) via _get_state_path()

CSV_REFRESH_MS = 500
TIMER_TICK_MS = 1000

HEAT_WARN_SEC = 3 * 60  # 3:00 m
HEAT_ALERT_FLASH_SEC = 4 * 60 + 30  # 4:30 m (start flashing)
HEAT_ALERT_SOLID_SEC = 5 * 60  # 5:00 m (red + flash remain)
# -------------------- Constants & Config (end)


# -------------------- Small helpers (start)
def fmt_time_human(seconds: int) -> str:
    """Format like '20s', '1:20s', '10:00s' (no spaces, always 's' suffix)."""
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}s"


def sign_from_side(is_long: Optional[bool]) -> int:
    if is_long is True:
        return 1
    if is_long is False:
        return -1
    return 0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def extract_symbol_display(full_symbol: str) -> str:
    """
    Extract 3-letter display symbol from full DTC symbol.
    Example: 'F.US.MESZ25' -> 'MES'
    If format doesn't match, return full symbol as-is.
    """
    try:
        # Look for pattern: *.US.XXX* where XXX are the 3 letters we want
        parts = full_symbol.split(".")
        for i, part in enumerate(parts):
            if part == "US" and i + 1 < len(parts):
                # Get the next part after 'US'
                next_part = parts[i + 1]
                if len(next_part) >= 3:
                    # Extract first 3 letters
                    return next_part[:3].upper()
        # Fallback: return as-is
        return full_symbol.strip().upper()
    except Exception:
        return full_symbol.strip().upper()


# -------------------- Small helpers (end)


# -------------------- Panel 2 Main (start)
# Note: MetricCell is now imported from widgets.metric_cell for consistency across panels
class Panel2(QtWidgets.QWidget, ThemeAwareMixin):
    """
    Panel 2 — Live trading metrics, 3x5 grid layout. Live CSV feed (500 ms),
    Duration/Heat timers with persistence, state-change logging.
    """

    tradesChanged = QtCore.pyqtSignal(object)

    tradesChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # CRITICAL: (mode, account) scoping
        self.current_mode: str = "SIM"
        self.current_account: str = ""

        self.symbol: str = "ES"  # Default symbol, updated via set_symbol()
        self.entry_price: Optional[float] = None  # NEVER pre-populated from cache
        self.entry_qty: int = 0  # NEVER pre-populated from cache
        self.is_long: Optional[bool] = None  # NEVER pre-populated from cache
        self.target_price: Optional[float] = None
        self.stop_price: Optional[float] = None

        # Feed state (live, continuously updated from CSV)
        self.last_price: Optional[float] = None
        self.session_high: Optional[float] = None
        self.session_low: Optional[float] = None
        self.vwap: Optional[float] = None
        self.cum_delta: Optional[float] = None
        self.poc: Optional[float] = None

        # Entry snapshots (captured once at position entry, static)
        self.entry_vwap: Optional[float] = None
        self.entry_delta: Optional[float] = None
        self.entry_poc: Optional[float] = None

        # Timer state (persisted)
        self.entry_time_epoch: Optional[int] = None  # when trade began
        self.heat_start_epoch: Optional[int] = None  # when drawdown began
        # Per-trade extremes for MAE/MFE
        self._trade_min_price: Optional[float] = None
        self._trade_max_price: Optional[float] = None

        # Timeframe state (for pills & pulsing dot)
        self._tf: str = "LIVE"
        self._pnl_up: Optional[bool] = None  # optional hint for pill color

        # Build UI and timers
        self._build()
        self._setup_timers()

        # Load scoped state after UI is built
        try:
            self._load_state()
        except Exception as e:
            log.warning(f"[Panel2] Failed to load initial state: {e}")

        # First paint
        self._refresh_all_cells(initial=True)

        # Apply current theme colors (in case theme was switched before this panel was created)
        self.refresh_theme()

    # -------------------- Trade persistence hooks (start)
    def notify_trade_closed(self, trade: dict) -> None:
        """External hook to persist a closed trade and notify listeners.
        Expects keys: symbol, side, qty, entry_price, exit_price, realized_pnl,
        optional: entry_time, exit_time, commissions, r_multiple, mae, mfe, account.
        """
        # Get current balance BEFORE processing
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            account = trade.get("account", "")
            mode = "SIM" if account.lower().startswith("sim") else "LIVE"
            balance_before = state.get_balance_for_mode(mode) if state else None
        except Exception:
            balance_before = None
            mode = "UNKNOWN"

        # Log trade close summary
        symbol = trade.get("symbol", "UNKNOWN")
        pnl = trade.get("realized_pnl", 0)
        pnl_sign = "+" if pnl >= 0 else ""
        entry = trade.get("entry_price", "?")
        exit_p = trade.get("exit_price", "?")
        qty = trade.get("qty", "?")

        # Simple one-line trade close notification
        print(f"[TRADE CLOSE] {symbol} {qty} @ {entry} → {exit_p} | P&L: {pnl_sign}${abs(pnl):,.2f} | Mode: {mode}")
        try:
            from services.trade_service import TradeManager
            from core.app_state import get_state_manager

            state = get_state_manager()
            trade_manager = TradeManager(state_manager=state)
        except Exception as e:
            trade_manager = None
        ok = False
        try:
            if trade_manager:
                # Extract account from trade dict for mode detection
                account = trade.get("account", "")

                # Create pos_info dict from trade data
                pos_info = {
                    "qty": trade.get("qty", 0),
                    "entry_price": trade.get("entry_price", 0),
                    "entry_time": trade.get("entry_time"),
                    "account": account,
                }

                # Call record_closed_trade with proper signature
                try:
                    ok = trade_manager.record_closed_trade(
                        symbol=trade.get("symbol", ""),
                        pos_info=pos_info,
                        exit_price=trade.get("exit_price"),
                        realized_pnl=trade.get("realized_pnl"),
                        commissions=trade.get("commissions"),
                        r_multiple=trade.get("r_multiple"),
                        mae=trade.get("mae"),
                        mfe=trade.get("mfe"),
                        efficiency=trade.get("efficiency"),
                        # Account will be auto-detected in record_closed_trade
                    )
                except Exception as method_error:
                    import traceback
                    traceback.print_exc()
                    ok = False
        except Exception as e:
            from utils.logger import get_logger
            log = get_logger(__name__)
            log.error(f"[panel2] Error recording closed trade: {e}", exc_info=True)
            ok = False
        # Emit regardless; consumers may refresh their views
        try:
            payload = dict(trade)
            payload["ok"] = ok
            self.tradesChanged.emit(payload)
        except Exception as e:
            pass

    # -------------------- Trade persistence hooks (end)

    # -------------------- DTC Order handling (start)
    def on_order_update(self, payload: dict) -> None:
        """Handle normalized OrderUpdate from DTC (via data_bridge).
        Persists closed trades automatically and resets per-trade trackers.
        Seeds position from fill data when in SIM mode (Sierra Chart doesn't send non-zero PositionUpdate).
        Auto-detects stop and target orders from sell orders based on price relative to entry.

        Args:
            payload: Normalized order update dict from data_bridge (not raw DTC)
        """
        try:
            order_status = payload.get("OrderStatus")
            side = payload.get("BuySell")  # 1=Buy, 2=Sell
            price1 = payload.get("Price1")

            # Auto-detect stop/target from sell orders (regardless of fill status)
            if side == 2 and self.entry_price is not None and price1 is not None:
                price1 = float(price1)
                if price1 < self.entry_price:
                    # Lower price = Stop loss
                    self.stop_price = price1
                    self.c_stop.set_value_text(f"{price1:.2f}")
                    self.c_stop.set_value_color(THEME.get("text_primary"))
                    log.info(f"[panel2] Stop detected @ {price1:.2f}")
                elif price1 > self.entry_price:
                    # Higher price = Target
                    self.target_price = price1
                    self.c_target.set_value_text(f"{price1:.2f}")
                    self.c_target.set_value_color(THEME.get("text_primary"))
                    log.info(f"[panel2] Target detected @ {price1:.2f}")

            # Process fills (Status 3=Filled, 7=Filled)
            if order_status not in (3, 7):
                return

            # SIM mode workaround: Seed position from fill if we don't have one yet
            # (Sierra Chart in SIM mode never sends non-zero PositionUpdate, only qty=0)
            qty = payload.get("FilledQuantity") or 0
            price = payload.get("AverageFillPrice") or payload.get("Price1")
            is_long = side == 1

            if qty > 0 and price is not None:
                # Only seed if we're currently flat (no existing position)
                if not (self.entry_qty and self.entry_price is not None and self.is_long is not None):
                    print(f"  Position was flat, seeding from fill")
                    print(f"  qty={qty}, price={price}, is_long={is_long}")
                    self.set_position(qty, price, is_long)
                    log.info(f"[panel2] Seeded position from fill: qty={qty}, price={price}, long={is_long}")
                    print(f"  [OK] Early return - will NOT call notify_trade_closed()\n")
                    return  # Early exit - don't process as close since we just opened

            # Require we have an active position context for closing logic
            if not (self.entry_qty and self.entry_price is not None and self.is_long is not None):
                return

            # CRITICAL FIX: Only process as a CLOSE if quantity is DECREASING
            # If qty stayed the same or increased, this is NOT a close - skip it!
            current_qty = self.entry_qty if self.entry_qty else 0
            print(f"  Current position qty: {current_qty}")
            print(f"  Incoming fill qty: {qty}")
            print(f"  Order side (1=Buy, 2=Sell): {side}")
            print(f"  Is long position: {self.is_long}")

            # If incoming qty >= current qty, this is adding to or maintaining position, not closing
            if qty >= current_qty:
                print(f"  SKIP: qty is not decreasing (fill={qty}, current={current_qty})")
                print(f"  This is likely a pyramid/add position, not a close\n")
                return

            # If we reach here, it's a CLOSE
            print(f"  CLOSE DETECTED: qty decreased from {current_qty} to {qty}")

            # Extract exit price from payload
            exit_price = (
                payload.get("LastFillPrice")
                or payload.get("AverageFillPrice")
                or payload.get("Price1")
                or self.last_price
            )
            if exit_price is None:
                log.warning("[panel2] Fill detected but no exit price available")
                return
            exit_price = float(exit_price)

            qty = int(abs(self.entry_qty))
            side = "long" if self.is_long else "short"
            entry_price = float(self.entry_price)

            # Use centralized trading constants
            sign = 1.0 if self.is_long else -1.0
            realized_pnl = (exit_price - entry_price) * sign * qty * DOLLARS_PER_POINT
            commissions = COMM_PER_CONTRACT * qty

            # r-multiple if stop available
            r_multiple = None
            if self.stop_price is not None and float(self.stop_price) > 0:
                risk_per_contract = abs(entry_price - float(self.stop_price)) * DOLLARS_PER_POINT
                if risk_per_contract > 0:
                    r_multiple = realized_pnl / (risk_per_contract * qty)

            # MAE/MFE in PnL units using tracked extremes
            # LONG: MAE from min (adverse), MFE from max (favorable)
            # SHORT: MAE from max (adverse), MFE from min (favorable)
            mae = None
            mfe = None
            efficiency = None
            try:
                if self._trade_min_price is not None and self._trade_max_price is not None:
                    if self.is_long:
                        mae_pts = min(0.0, self._trade_min_price - entry_price)
                        mfe_pts = max(0.0, self._trade_max_price - entry_price)
                    else:  # SHORT
                        mae_pts = min(0.0, entry_price - self._trade_max_price)
                        mfe_pts = max(0.0, entry_price - self._trade_min_price)
                    mae = mae_pts * DOLLARS_PER_POINT * qty
                    mfe = mfe_pts * DOLLARS_PER_POINT * qty

                    # Calculate efficiency: (realized PnL / MFE) if MFE > 0
                    if mfe > 0 and realized_pnl is not None:
                        # Efficiency = realized profit / maximum potential profit
                        # Expressed as decimal (0.0 to 1.0, where 1.0 = 100% efficient)
                        # Can exceed 1.0 if trail added profit beyond max seen during trade
                        efficiency = realized_pnl / mfe
            except Exception:
                pass

            # entry/exit times
            from datetime import datetime
            from datetime import timezone as _tz

            entry_time = datetime.fromtimestamp(self.entry_time_epoch, tz=UTC) if self.entry_time_epoch else None
            # Use DTC timestamp from payload
            exit_ts = payload.get("DateTime")
            exit_time = datetime.fromtimestamp(float(exit_ts), tz=UTC) if exit_ts else datetime.now(tz=UTC)

            # Get account for mode detection (SIM vs LIVE)
            account = payload.get("TradeAccount") or ""

            trade = {
                "symbol": payload.get("Symbol") or "",
                "side": side,
                "qty": qty,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "realized_pnl": realized_pnl,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "commissions": commissions,
                "r_multiple": r_multiple,
                "mae": mae,
                "mfe": mfe,
                "efficiency": efficiency,
                "account": account,  # ← Include account for mode detection (SIM/LIVE)
            }

            print(f"  Symbol: {trade['symbol']}")
            print(f"  Side: {trade['side']}")
            print(f"  Qty: {trade['qty']}")
            print(f"  Entry: ${trade['entry_price']:.2f}")
            print(f"  Exit: ${trade['exit_price']:.2f}")
            print(f"  PnL: ${trade['realized_pnl']:,.2f}")
            print(f"  Account: {trade['account']}")

            self.notify_trade_closed(trade)

            # Reset position context after close
            self.set_position(0, 0.0, None)
        except Exception as e:
            log.error(f"[panel2] on_order_update error: {e}")

    # -------------------- DTC Order handling (end)

    def on_position_update(self, payload: dict) -> None:
        """Handle normalized PositionUpdate from DTC and mirror into local state.
        Detects trade closure when position goes from non-zero to zero.

        Args:
            payload: Normalized position update dict from MessageRouter (lowercase keys)
        """
        try:
            # Extract from normalized payload (lowercase keys from data_bridge normalization)
            qty = int(payload.get("qty", 0))
            avg_price = payload.get("avg_entry")

            # CRITICAL: Extract symbol from PositionUpdate payload (NOT from quote feed)
            # Try both lowercase (normalized) and uppercase (raw DTC) keys
            symbol = payload.get("symbol") or payload.get("Symbol") or ""

            # Convert to float if not None
            if avg_price is not None:
                avg_price = float(avg_price)

            # CRITICAL: Reject positions without valid price data (avoid cached stale data)
            if qty != 0 and avg_price is None:
                log.warning(
                    f"[panel2] Rejecting position with qty={qty} but missing price"
                )
                return

            # Determine direction
            is_long = None if qty == 0 else (qty > 0)

            # CRITICAL: Update symbol from PositionUpdate payload (BEFORE set_position)
            # This ensures symbol comes from the live position, not the quote feed
            if symbol:
                self.symbol = extract_symbol_display(symbol)
                log.info(f"[panel2] Symbol updated from PositionUpdate: {symbol} -> {self.symbol}")

                # Immediately update header banner to show new symbol
                if hasattr(self, "symbol_banner"):
                    self.symbol_banner.setText(self.symbol)

            # CRITICAL: Detect trade closure - position went from non-zero to zero
            if qty == 0 and self.entry_qty and self.entry_qty > 0 and self.entry_price is not None and self.is_long is not None:

                # Use last price as exit price (position already closed, we don't have fill price here)
                exit_price = self.last_price if self.last_price else self.entry_price

                # Build trade dict
                from datetime import datetime
                from datetime import timezone as _tz

                entry_time = datetime.fromtimestamp(self.entry_time_epoch, tz=UTC) if self.entry_time_epoch else None
                exit_time = datetime.now(tz=UTC)

                qty_val = int(abs(self.entry_qty))
                side = "long" if self.is_long else "short"
                entry_price_val = float(self.entry_price)

                # Calculate P&L
                sign = 1.0 if self.is_long else -1.0
                realized_pnl = (exit_price - entry_price_val) * sign * qty_val * DOLLARS_PER_POINT
                commissions = COMM_PER_CONTRACT * qty_val

                # r-multiple if stop available
                r_multiple = None
                if self.stop_price is not None and float(self.stop_price) > 0:
                    risk_per_contract = abs(entry_price_val - float(self.stop_price)) * DOLLARS_PER_POINT
                    if risk_per_contract > 0:
                        r_multiple = realized_pnl / (risk_per_contract * qty_val)

                # MAE/MFE
                mae = None
                mfe = None
                try:
                    if self._trade_min_price is not None and self._trade_max_price is not None:
                        if self.is_long:
                            mae_pts = min(0.0, self._trade_min_price - entry_price_val)
                            mfe_pts = max(0.0, self._trade_max_price - entry_price_val)
                        else:
                            mae_pts = min(0.0, entry_price_val - self._trade_max_price)
                            mfe_pts = max(0.0, entry_price_val - self._trade_min_price)
                        mae = mae_pts * DOLLARS_PER_POINT * qty_val
                        mfe = mfe_pts * DOLLARS_PER_POINT * qty_val
                except Exception:
                    pass

                # Get account for mode detection
                account = payload.get("TradeAccount") or ""

                trade = {
                    "symbol": self.symbol or "",
                    "side": side,
                    "qty": qty_val,
                    "entry_price": entry_price_val,
                    "exit_price": exit_price,
                    "realized_pnl": realized_pnl,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "commissions": commissions,
                    "r_multiple": r_multiple,
                    "mae": mae,
                    "mfe": mfe,
                    "account": account,
                }

                print(f"  PnL: ${realized_pnl:,.2f}, account={account}")
                print(f"  Calling notify_trade_closed()...\n")

                # Persist the trade
                self.notify_trade_closed(trade)

            # Update position state (ONLY if we have valid data)
            if qty == 0 or avg_price is not None:
                # Store entry price and quantity explicitly
                self.entry_price = avg_price if qty != 0 else None
                self.entry_qty = abs(qty) if qty != 0 else 0

                # Call set_position to update timers and capture snapshots
                self.set_position(abs(qty), avg_price, is_long)
                log.info(f"[panel2] Position update accepted: symbol={self.symbol}, qty={qty}, avg={avg_price}, long={is_long}")

                # Ensure UI refresh happens
                self._refresh_all_cells()
            else:
                log.warning(f"[panel2] Invalid position data - skipping: qty={qty}, avg={avg_price}")
        except Exception as e:
            log.error(f"[panel2] on_position_update error: {e}", exc_info=True)

    # -------------------- UI Build (start)
    def _build(self):
        self.setObjectName("Panel2")
        self.setStyleSheet(f"QWidget#Panel2 {{ background:{THEME.get('bg_panel', '#0B0F14')}; }}")

        # Outer column layout for header + grid
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # ---- Timeframe pills (top, centered)
        from widgets.timeframe_pills import InvestingTimeframePills  # type: ignore

        self.pills = InvestingTimeframePills()
        if hasattr(self.pills, "timeframeChanged"):
            try:
                self.pills.timeframeChanged.connect(
                    self._on_timeframe_changed,
                    type=QtCore.Qt.ConnectionType.UniqueConnection,
                )
            except Exception:
                self.pills.timeframeChanged.connect(self._on_timeframe_changed)

        pills_row = QtWidgets.QHBoxLayout()
        pills_row.setContentsMargins(0, 0, 0, 0)
        pills_row.setSpacing(0)
        pills_row.addStretch(1)
        pills_row.addWidget(self.pills, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        pills_row.addStretch(1)
        outer.addLayout(pills_row)

        # Initialize live dot state/color
        try:
            if hasattr(self.pills, "set_live_dot_visible"):
                self.pills.set_live_dot_visible(True)
            if hasattr(self.pills, "set_live_dot_pulsing"):
                self.pills.set_live_dot_pulsing(self._tf == "LIVE")
            if hasattr(self.pills, "set_active_color"):
                color = (
                    ColorTheme.pnl_color_from_direction(self._pnl_up)
                    if self._pnl_up is not None
                    else THEME.get("pnl_neu_color")
                )
                self.pills.set_active_color(color)
        except Exception:
            pass

        # ---- Live Position header (horizontal layout: title, symbol, and price on same row)
        hdr = QtWidgets.QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 4)
        hdr.setSpacing(20)

        # Symbol label (left) - shows "--" when flat, populated from DTC order update
        # Uses heading font (Lato in LIVE/SIM)
        self.symbol_banner = QtWidgets.QLabel("--", self)
        self.symbol_banner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.symbol_banner.setFont(
            ColorTheme.heading_qfont(
                int(THEME.get("title_font_weight")),
                int(THEME.get("title_font_size")),
            )
        )
        self.symbol_banner.setStyleSheet(f"color: {THEME.get('ink')};")

        # Live price label (right) - shows "FLAT" when not in position, current market price when in position
        # Uses heading font (Lato in LIVE/SIM)
        self.live_banner = QtWidgets.QLabel("FLAT", self)
        self.live_banner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.live_banner.setFont(
            ColorTheme.heading_qfont(
                int(THEME.get("title_font_weight")),
                int(THEME.get("title_font_size")),
            )
        )
        self.live_banner.setStyleSheet(f"color: {THEME.get('ink')};")

        # Center both header items in a single row
        hdr.addStretch(1)
        hdr.addWidget(self.symbol_banner)
        hdr.addWidget(self.live_banner)
        hdr.addStretch(1)
        outer.addLayout(hdr)

        # ---- Metric grid (3 rows × 5 columns)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        outer.addLayout(grid, 1)

        # Row 1
        self.c_price = MetricCell("Price")
        self.c_heat = MetricCell("Heat")
        self.c_time = MetricCell("Time")
        self.c_target = MetricCell("Target")
        self.c_stop = MetricCell("Stop")

        # Row 2
        self.c_risk = MetricCell("Planned Risk")
        self.c_rmult = MetricCell("R-Multiple")
        self.c_range = MetricCell("Range")
        self.c_mae = MetricCell("MAE")
        self.c_mfe = MetricCell("MFE")

        # Row 3
        self.c_vwap = MetricCell("VWAP")
        self.c_delta = MetricCell("Delta")
        self.c_poc = MetricCell("POC")
        self.c_eff = MetricCell("Efficiency")
        self.c_pts = MetricCell("Pts")

        cells = [
            (0, 0, self.c_price),
            (0, 1, self.c_heat),
            (0, 2, self.c_time),
            (0, 3, self.c_target),
            (0, 4, self.c_stop),
            (1, 0, self.c_risk),
            (1, 1, self.c_rmult),
            (1, 2, self.c_range),
            (1, 3, self.c_mae),
            (1, 4, self.c_mfe),
            (2, 0, self.c_vwap),
            (2, 1, self.c_delta),
            (2, 2, self.c_poc),
            (2, 3, self.c_eff),
            (2, 4, self.c_pts),
        ]
        for r, c, w in cells:
            grid.addWidget(w, r, c)

    # -------------------- UI Build (end)

    # -------------------- Timers & Feed (start)
    def _setup_timers(self):
        # CSV feed timer - provides live market data for calculations
        # CSV contains: last (live price), high, low, vwap, cum_delta
        # Used for: P&L, MAE, MFE, heat tracking, VWAP analysis
        self._csv_timer = QtCore.QTimer(self)
        self._csv_timer.setInterval(CSV_REFRESH_MS)
        self._csv_timer.timeout.connect(self._on_csv_tick)
        self._csv_timer.start()

        # Duration/Heat tick
        self._clock_timer = QtCore.QTimer(self)
        self._clock_timer.setInterval(TIMER_TICK_MS)
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._clock_timer.start()

        # Flash is per-cell (handled internally by MetricCell)

    def _on_csv_tick(self):
        """
        CSV feed tick handler.

        DATA SOURCE CLARIFICATION:
        - CSV file (snapshot.csv) provides: last, high, low, vwap, cum_delta
          * 'last' = live market price (for P&L and heat calculations)
          * 'high'/'low' = session extremes (for MAE/MFE)
          * 'vwap' = volume-weighted average price
          * 'cum_delta' = cumulative delta
        - DTC messages provide: entry price, position qty, order status
          * Price cell shows entry price from DTC (e.g., "2 @ 5800.25")
          * Live price from CSV is NOT displayed but used for calculations
        """
        prev = (self.last_price, self.session_high, self.session_low, self.vwap, self.cum_delta)
        updated = self._read_snapshot_csv()
        if not updated:
            return

        # Log state changes only
        if self.vwap != prev[3]:
            log.info(f"[panel2] Feed updated — VWAP changed: {self.vwap}")
        if self.cum_delta != prev[4]:
            log.info(f"[panel2] Feed updated — Delta changed: {self.cum_delta}")

        # Heat transitions (drawdown tracking)
        self._update_heat_state_transitions(prev[0], self.last_price)
        # Track per-trade min/max while in position for MAE/MFE
        try:
            if self.entry_qty and self.last_price is not None:
                p = float(self.last_price)
                if self._trade_min_price is None or p < self._trade_min_price:
                    self._trade_min_price = p
                if self._trade_max_price is None or p > self._trade_max_price:
                    self._trade_max_price = p
        except Exception:
            pass

        # UI update
        self._refresh_all_cells()

        # Proximity alerts
        self._update_proximity_alerts()

        # Update the non-cell banner
        self._update_live_banner()

    def _on_clock_tick(self):
        # Just update time/heat text and color thresholds every second
        self._update_time_and_heat_cells()

    def _read_snapshot_csv(self) -> bool:
        """
        Header-aware CSV reader:
          - Expects header row: last,high,low,vwap,cum_delta,poc
          - Uses FIRST data row after the header (row 2)
          - Robust to BOM and column re-ordering
        """
        try:
            with open(CSV_FEED_PATH, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                row = next(reader, None)  # first data row after header
                if not row:
                    return False

                def fnum(key: str) -> float:
                    val = (row.get(key, "") or "").strip()
                    if not val:
                        return 0.0  # Default to 0.0 for empty values
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                self.last_price = fnum("last")
                self.session_high = fnum("high")
                self.session_low = fnum("low")
                self.vwap = fnum("vwap")
                self.cum_delta = fnum("cum_delta")
                self.poc = fnum("poc")
                return True

        except FileNotFoundError:
            static_key = "_missing_csv_logged"
            if not getattr(self, static_key, False):
                log.warning(f"[panel2] Snapshot CSV not found at: {CSV_FEED_PATH}")
                setattr(self, static_key, True)
            return False
        except StopIteration:
            # Header exists but no data rows yet
            return False
        except Exception as e:
            log.error(f"[panel2] CSV read error: {e}")
            return False

    # -------------------- Timers & Feed (end)

    # -------------------- Persistence (start)
    def _get_state_path(self) -> str:
        """
        Get scoped state file path for current (mode, account).

        Returns:
            Path to state file: data/runtime_state_panel2_{mode}_{account}.json
        """
        from utils.atomic_persistence import get_scoped_path
        path = get_scoped_path("runtime_state_panel2", self.current_mode, self.current_account)
        return str(path)

    def _load_state(self):
        """
        Load session state from scoped state file.
        Uses atomic_persistence for safe loading.
        """
        try:
            from utils.atomic_persistence import load_json_atomic

            state_path = self._get_state_path()
            data = load_json_atomic(state_path)

            if data:
                self.entry_time_epoch = data.get("entry_time_epoch")
                self.heat_start_epoch = data.get("heat_start_epoch")
                self._trade_min_price = data.get("trade_min_price")
                self._trade_max_price = data.get("trade_max_price")
                log.info(f"[Panel2] Restored session timers from {state_path}")
            else:
                log.debug(f"[Panel2] No persisted state found for {self.current_mode}/{self.current_account}")
        except Exception as e:
            log.warning(f"[Panel2] Failed to load persisted state: {e}")

    def _save_state(self):
        """
        Save session state to scoped state file.
        Uses atomic_persistence for safe writes.
        """
        try:
            from pathlib import Path
            from utils.atomic_persistence import save_json_atomic

            state_path = Path(self._get_state_path())

            data = {
                "entry_time_epoch": self.entry_time_epoch,
                "heat_start_epoch": self.heat_start_epoch,
                "trade_min_price": self._trade_min_price,
                "trade_max_price": self._trade_max_price,
                "mode": self.current_mode,
                "account": self.current_account,
            }

            success = save_json_atomic(data, state_path)
            if success:
                log.debug(f"[Panel2] Saved session state for {self.current_mode}/{self.current_account}")
        except Exception as e:
            log.error(f"[Panel2] Persist write failed: {e}")

    def set_trading_mode(self, mode: str, account: Optional[str] = None) -> None:
        """
        Update trading mode for this panel.

        CRITICAL: This implements the ModeChanged contract:
        1. Freeze current state (save to current scope)
        2. Swap to new (mode, account) scope
        3. Reload session state from new scope
        4. Single repaint

        Args:
            mode: Trading mode ("SIM", "LIVE", "DEBUG")
            account: Account identifier (optional, defaults to empty string)
        """
        mode = mode.upper()
        if mode not in ("DEBUG", "SIM", "LIVE"):
            log.warning(f"[Panel2] Invalid trading mode: {mode}")
            return

        # Use empty string if account not provided
        if account is None:
            account = ""

        # Check if mode/account actually changed
        if mode == self.current_mode and account == self.current_account:
            log.debug(f"[Panel2] Mode/account unchanged: {mode}, {account}")
            return

        old_scope = (self.current_mode, self.current_account)
        new_scope = (mode, account)
        log.info(f"[Panel2] Mode change: {old_scope} → {new_scope}")

        # 1. Freeze: Save current state to old scope
        self._save_state()

        # 2. Swap: Update active scope
        self.current_mode = mode
        self.current_account = account

        # 3. Reload: Load state from new scope
        self._load_state()

        # 4. Single repaint: Refresh all cells
        self._refresh_all_cells()
        self._update_live_banner()

        log.info(f"[Panel2] Switched to {mode}/{account}")

    # -------------------- Persistence (end)

    # -------------------- Position Interface (start)
    # These setters can be called by your DTC/router when a trade opens/updates.
    def set_position(self, qty: int, entry_price: float, is_long: Optional[bool]):
        self.entry_qty = max(0, int(qty))

        # Start duration timer if entering a position
        if self.entry_qty > 0 and entry_price is not None:
            self.entry_price = float(entry_price)
            self.is_long = is_long
            if not self.entry_time_epoch:
                self.entry_time_epoch = int(time.time())
                # Capture VWAP, Delta, and POC snapshots at entry (static values)
                self.entry_vwap = self.vwap
                self.entry_delta = self.cum_delta
                self.entry_poc = self.poc
                # Initialize trade extremes to entry price (prevents premature MAE/MFE)
                self._trade_min_price = self.entry_price
                self._trade_max_price = self.entry_price
                log.info(
                    f"[panel2] Position opened — Entry VWAP: {self.entry_vwap}, Entry Delta: {self.entry_delta}, Entry POC: {self.entry_poc}"
                )
        else:
            # No position - clear all position-specific data
            self.entry_price = None
            self.is_long = None
            self.target_price = None
            self.stop_price = None
            self.entry_vwap = None
            self.entry_delta = None
            self.entry_poc = None
            self.entry_time_epoch = None
            self.heat_start_epoch = None
            # Clear trade extremes (MAE/MFE tracking)
            self._trade_min_price = None
            self._trade_max_price = None
            log.info("[panel2] Position closed — all position data cleared")
        self._save_state()
        self._refresh_all_cells()
        self._update_live_banner()

    def set_targets(self, target_price: Optional[float], stop_price: Optional[float]):
        self.target_price = float(target_price) if target_price is not None else None
        self.stop_price = float(stop_price) if stop_price is not None else None
        self._refresh_all_cells()
        self._update_live_banner()

    def set_symbol(self, symbol: str):
        """
        Update the symbol label (called from DTC handshake or external source).
        Extracts 3-letter display symbol from full DTC symbol.
        Example: 'F.US.MESZ25' -> 'MES'
        """
        self.symbol = symbol.strip().upper() if symbol else "ES"
        # Extract display symbol (3 letters after "US.")
        display_symbol = extract_symbol_display(self.symbol)
        if hasattr(self, "symbol_banner"):
            self.symbol_banner.setText(display_symbol)

    # -------------------- Position Interface (end)

    # -------------------- Timeframe handling (start)
    @QtCore.pyqtSlot(str)
    def _on_timeframe_changed(self, tf: str) -> None:
        if tf not in ("LIVE", "1D", "1W", "1M", "3M", "YTD"):
            return
        self._tf = tf
        # Update LIVE dot/pulse and color
        try:
            if hasattr(self.pills, "set_live_dot_visible"):
                self.pills.set_live_dot_visible(True)
            if hasattr(self.pills, "set_live_dot_pulsing"):
                self.pills.set_live_dot_pulsing(tf == "LIVE")
            if hasattr(self.pills, "set_active_color"):
                color = (
                    ColorTheme.pnl_color_from_direction(self._pnl_up)
                    if self._pnl_up is not None
                    else THEME.get("pnl_neu_color")
                )
                self.pills.set_active_color(color)
        except Exception:
            pass

    def refresh_pill_colors(self) -> None:
        """
        Force timeframe pills to refresh their colors from THEME.
        Called when trading mode switches (DEBUG/SIM/LIVE) to update pill colors.
        """
        try:
            if hasattr(self.pills, "set_active_color"):
                # Clear cached color to force refresh
                if hasattr(self.pills, "_last_active_hex"):
                    delattr(self.pills, "_last_active_hex")
                # Re-read color from THEME and apply
                color = (
                    ColorTheme.pnl_color_from_direction(self._pnl_up)
                    if self._pnl_up is not None
                    else THEME.get("pnl_neu_color")
                )
                self.pills.set_active_color(color)
        except Exception:
            pass

    # -------------------- Timeframe handling (end)

    # -------------------- Update & Rendering (start)
    def _refresh_all_cells(self, initial: bool = False):
        # If flat (no position), set all cells to dashes and exit
        if not (getattr(self, "entry_qty", 0) and self.entry_price is not None):
            dim_color = THEME.get("text_dim")
            # Set all 15 cells to "--"
            self.c_price.set_value_text("--")
            self.c_price.set_value_color(dim_color)
            self.c_heat.set_value_text("--")
            self.c_heat.set_value_color(dim_color)
            self.c_heat.stop_flashing()
            self.c_time.set_value_text("--")
            self.c_time.set_value_color(dim_color)
            self.c_target.set_value_text("--")
            self.c_target.set_value_color(dim_color)
            self.c_stop.set_value_text("--")
            self.c_stop.set_value_color(dim_color)
            self.c_stop.stop_flashing()
            self.c_risk.set_value_text("--")
            self.c_risk.set_value_color(dim_color)
            self.c_rmult.set_value_text("--")
            self.c_rmult.set_value_color(dim_color)
            self.c_range.set_value_text("--")
            self.c_range.set_value_color(dim_color)
            self.c_mae.set_value_text("--")
            self.c_mae.set_value_color(dim_color)
            self.c_mfe.set_value_text("--")
            self.c_mfe.set_value_color(dim_color)
            self.c_vwap.set_value_text("--")
            self.c_vwap.set_value_color(dim_color)
            self.c_delta.set_value_text("--")
            self.c_delta.set_value_color(dim_color)
            self.c_poc.set_value_text("--")
            self.c_poc.set_value_color(dim_color)
            self.c_eff.set_value_text("--")
            self.c_eff.set_value_color(dim_color)
            self.c_pts.set_value_text("--")
            self.c_pts.set_value_color(dim_color)

            # Update banner to show "LIVE POSITION" and "FLAT"
            self._update_live_banner()
            return

        # Only calculate values if we have a position
        # Price cell: "QTY @ ENTRY" all green/red by direction
        self._update_price_cell()

        # Time & Heat (text & color thresholds)
        self._update_time_and_heat_cells()

        # Target / Stop (and stop flashing if within 1.0 pt)
        self._update_target_stop_cells()

        # Risk, R, Range, MAE, MFE, VWAP, Delta, Efficiency, Pts, $PnL
        self._update_secondary_metrics()

        # Keep the banner in sync with the latest price
        self._update_live_banner()

        if initial:
            log.info("[panel2] UI initialized — metrics grid active")

    def _update_price_cell(self):
        # Position guaranteed to exist when this is called
        txt = f"{self.entry_qty} @ {self.entry_price:.2f}"
        color = ColorTheme.pnl_color_from_direction(self.is_long)
        self.c_price.set_value_text(txt)
        self.c_price.set_value_color(color)

    def _update_time_and_heat_cells(self):
        # Duration
        if self.entry_time_epoch:
            dur_sec = int(time.time() - self.entry_time_epoch)
            self.c_time.set_value_text(fmt_time_human(dur_sec))
            self.c_time.set_value_color(THEME.get("text_primary"))
        else:
            self.c_time.set_value_text("--")
            self.c_time.set_value_color(THEME.get("text_dim"))

        # Heat: measured only when in drawdown relative to entry
        has_position = bool(getattr(self, "entry_qty", 0) and self.entry_qty > 0)

        if not has_position:
            # No position - show "--"
            self.c_heat.set_value_text("--")
            self.c_heat.set_value_color(THEME.get("text_dim"))
            self.c_heat.stop_flashing()
        else:
            # In position - calculate and display heat
            heat_sec = 0
            if self.entry_price is not None and self.last_price is not None and self.is_long is not None:
                in_dd = (self.last_price < self.entry_price) if self.is_long else (self.last_price > self.entry_price)
                if in_dd:
                    if self.heat_start_epoch is None:
                        self.heat_start_epoch = int(time.time())
                        log.info("[panel2] Heat timer started (drawdown detected)")
                else:
                    if self.heat_start_epoch is not None:
                        log.info("[panel2] Heat timer paused (drawdown ended)")
                    self.heat_start_epoch = None

            if self.heat_start_epoch is not None:
                heat_sec = int(time.time() - self.heat_start_epoch)

            self.c_heat.set_value_text(fmt_time_human(heat_sec))

            # Heat color/flash thresholds
            if heat_sec == 0 or heat_sec < HEAT_WARN_SEC:
                self.c_heat.set_value_color(THEME.get("text_dim"))
                self.c_heat.stop_flashing()
            elif heat_sec < HEAT_ALERT_FLASH_SEC:
                self.c_heat.set_value_color(THEME.get("accent_warning"))
                self.c_heat.stop_flashing()
            else:
                # Flash with border color matching text color
                if heat_sec >= HEAT_ALERT_SOLID_SEC:
                    flash_color = THEME.get("accent_alert")
                    self.c_heat.set_value_color(flash_color)
                    self.c_heat.start_flashing(border_color=flash_color)
                else:
                    flash_color = THEME.get("accent_warning")
                    self.c_heat.set_value_color(flash_color)
                    self.c_heat.start_flashing(border_color=flash_color)

    def _update_target_stop_cells(self):
        # Target
        if self.target_price is not None:
            self.c_target.set_value_text(f"{self.target_price:.2f}")
            self.c_target.set_value_color(THEME.get("text_primary"))
        else:
            self.c_target.set_value_text("--")
            self.c_target.set_value_color(THEME.get("text_dim"))

        # Stop (flash when price within 1.0 point of stop)
        if self.stop_price is not None:
            self.c_stop.set_value_text(f"{self.stop_price:.2f}")
            near = False
            if self.last_price is not None and abs(self.last_price - self.stop_price) <= 1.0:
                near = True
            if near:
                self.c_stop.set_value_color(THEME.get("accent_alert"))
                self.c_stop.start_flashing()
            else:
                self.c_stop.set_value_color(THEME.get("text_primary"))
                self.c_stop.stop_flashing()
        else:
            self.c_stop.set_value_text("--")
            self.c_stop.set_value_color(THEME.get("text_dim"))
            self.c_stop.stop_flashing()

    def _update_secondary_metrics(self):
        # Position guaranteed to exist when this is called

        # CRITICAL: Validate that we have all necessary data from PositionUpdate
        # before calculating risk metrics (entry_price, stop_price, target_price)
        if self.entry_price is None:
            # No entry price from PositionUpdate - cannot calculate risk
            self.c_risk.set_value_text("--")
            self.c_risk.set_value_color(THEME.get("text_dim"))
            self.c_rmult.set_value_text("--")
            self.c_rmult.set_value_color(THEME.get("text_dim"))
            return

        # Planned Risk (always red, no negative sign shown)
        # Formula: |entry - stop| * $50/point * qty + commission
        if self.stop_price is not None:
            dist_pts = abs(self.entry_price - self.stop_price)
            dollars = dist_pts * DOLLARS_PER_POINT * self.entry_qty
            comm = COMM_PER_CONTRACT * self.entry_qty
            planned = dollars + comm
            self.c_risk.set_value_text(f"${planned:,.2f}")
            self.c_risk.set_value_color(THEME.get("pnl_neg_color"))
        else:
            self.c_risk.set_value_text("--")
            self.c_risk.set_value_color(THEME.get("text_dim"))

        # R-Multiple = (Current - Entry) / (Entry - Stop)
        # Only calculate if we have all required values from PositionUpdate
        if self.stop_price is not None and self.last_price is not None and self.entry_price is not None:
            denom = self.entry_price - self.stop_price
            if abs(denom) > 1e-9:
                r_mult = (self.last_price - self.entry_price) / denom
                self.c_rmult.set_value_text(f"{r_mult:.2f} R")
                if r_mult > 0:
                    self.c_rmult.set_value_color(THEME.get("pnl_pos_color"))
                elif r_mult < 0:
                    self.c_rmult.set_value_color(THEME.get("pnl_neg_color"))
                else:
                    self.c_rmult.set_value_color(THEME.get("pnl_neu_color"))
            else:
                self.c_rmult.set_value_text("--")
                self.c_rmult.set_value_color(THEME.get("text_dim"))
        else:
            self.c_rmult.set_value_text("--")
            self.c_rmult.set_value_color(THEME.get("text_dim"))

        # Range = distance from target compared to live price (signed with +/−)
        if self.target_price is not None and self.last_price is not None:
            dist = (self.target_price - self.last_price) * (1 if self.is_long else -1)
            sign_char = "+" if dist >= 0 else "-"
            self.c_range.set_value_text(f"{sign_char}{abs(dist):.2f} pt")
            self.c_range.set_value_color(THEME.get("text_primary"))
        else:
            self.c_range.set_value_text("--")
            self.c_range.set_value_color(THEME.get("text_dim"))

        # MAE / MFE from TRADE extremes (not session extremes)
        # LONG: MAE from min (adverse), MFE from max (favorable)
        # SHORT: MAE from max (adverse), MFE from min (favorable)
        # These track min/max SINCE position entry, not session-wide
        if self._trade_min_price is not None and self._trade_max_price is not None:
            if self.is_long:
                mae_pts = min(0.0, self._trade_min_price - self.entry_price)
                mfe_pts = max(0.0, self._trade_max_price - self.entry_price)
            else:  # SHORT
                mae_pts = min(0.0, self.entry_price - self._trade_max_price)
                mfe_pts = max(0.0, self.entry_price - self._trade_min_price)

            self.c_mae.set_value_text(f"{mae_pts:.2f} pt")
            self.c_mae.set_value_color(THEME.get("pnl_neg_color") if mae_pts < 0 else THEME.get("pnl_neu_color"))

            self.c_mfe.set_value_text(f"{mfe_pts:.2f} pt")
            self.c_mfe.set_value_color(THEME.get("pnl_pos_color") if mfe_pts > 0 else THEME.get("pnl_neu_color"))
        else:
            self.c_mae.set_value_text("--")
            self.c_mae.set_value_color(THEME.get("text_dim"))
            self.c_mfe.set_value_text("--")
            self.c_mfe.set_value_color(THEME.get("text_dim"))

        # VWAP (static snapshot from entry) - only show when in position
        has_position = bool(getattr(self, "entry_qty", 0) and self.entry_qty > 0)
        if has_position and self.entry_vwap is not None:
            self.c_vwap.set_value_text(f"{self.entry_vwap:.2f}")
            color = THEME.get("text_primary")
            if self.entry_price is not None and self.is_long is not None:
                if self.is_long:
                    color = (
                        THEME.get("pnl_neg_color") if self.entry_vwap > self.entry_price else THEME.get("pnl_pos_color")
                    )
                else:
                    color = (
                        THEME.get("pnl_pos_color") if self.entry_vwap > self.entry_price else THEME.get("pnl_neg_color")
                    )
            self.c_vwap.set_value_color(color)
        else:
            self.c_vwap.set_value_text("--")
            self.c_vwap.set_value_color(THEME.get("text_dim"))

        # Delta (static snapshot from entry) - only show when in position
        if has_position and self.entry_delta is not None:
            self.c_delta.set_value_text(f"{self.entry_delta:,.0f}")
            if self.entry_delta > 0:
                self.c_delta.set_value_color(THEME.get("pnl_pos_color"))
            elif self.entry_delta < 0:
                self.c_delta.set_value_color(THEME.get("pnl_neg_color"))
            else:
                self.c_delta.set_value_color(THEME.get("pnl_neu_color"))
        else:
            self.c_delta.set_value_text("--")
            self.c_delta.set_value_color(THEME.get("text_dim"))

        # Efficiency = PnL / MFE_value; show 0 if MFE <= 0
        # Position guaranteed, so entry_price, last_price, is_long exist
        # Uses TRADE max price (not session high) for accurate MFE
        eff_val: Optional[float] = None
        if self.last_price is not None and self._trade_max_price is not None:
            # Calculate current P&L in points
            if self.is_long:
                pnl_pts = self.last_price - self.entry_price
                mfe_pts = max(0.0, self._trade_max_price - self.entry_price)
            else:  # SHORT
                pnl_pts = self.entry_price - self.last_price
                mfe_pts = max(0.0, self.entry_price - self._trade_min_price)

            # Calculate efficiency if MFE is positive
            if mfe_pts > 1e-9:
                eff_val = pnl_pts / mfe_pts

        if eff_val is None:
            self.c_eff.set_value_text("--")
            self.c_eff.set_value_color(THEME.get("text_dim"))
        else:
            self.c_eff.set_value_text(f"{eff_val:.2f}")
            if eff_val > 0.6:
                self.c_eff.set_value_color(THEME.get("pnl_pos_color"))
            elif eff_val >= 0.3:
                self.c_eff.set_value_color(THEME.get("accent_warning"))
            else:
                self.c_eff.set_value_color(THEME.get("pnl_neg_color"))

        # Points PnL
        # Position guaranteed, so entry_price, is_long exist
        if self.last_price is not None:
            pnl_pts = (self.last_price - self.entry_price) * (1 if self.is_long else -1)
            sign_char = "+" if pnl_pts >= 0 else "-"
            self.c_pts.set_value_text(f"{sign_char}{abs(pnl_pts):.2f} pt")
            self.c_pts.set_value_color(ColorTheme.pnl_color_from_value(pnl_pts))
        else:
            self.c_pts.set_value_text("--")
            self.c_pts.set_value_color(THEME.get("text_dim"))

        # POC (static snapshot from entry) - only show when in position
        # Uses same color logic as VWAP (quality signal based on entry vs POC)
        if has_position and self.entry_poc is not None:
            self.c_poc.set_value_text(f"{self.entry_poc:.2f}")
            color = THEME.get("text_primary")
            if self.entry_price is not None and self.is_long is not None:
                if self.is_long:
                    color = (
                        THEME.get("pnl_neg_color") if self.entry_poc > self.entry_price else THEME.get("pnl_pos_color")
                    )
                else:
                    color = (
                        THEME.get("pnl_pos_color") if self.entry_poc > self.entry_price else THEME.get("pnl_neg_color")
                    )
            self.c_poc.set_value_color(color)
        else:
            self.c_poc.set_value_text("--")
            self.c_poc.set_value_color(THEME.get("text_dim"))

    def _update_live_banner(self) -> None:
        """Update symbol and live price display."""
        if not hasattr(self, "live_banner") or not hasattr(self, "symbol_banner"):
            return

        # Check if we have an active position
        has_position = bool(self.entry_qty and self.entry_qty > 0)

        # Symbol (left) - shows "--" when flat, symbol when in position
        if has_position:
            self.symbol_banner.setText(self.symbol)
        else:
            self.symbol_banner.setText("--")

        # Live price (right) - shows "FLAT" when not in position, current market price when in position
        if has_position:
            if self.last_price is not None:
                self.live_banner.setText(f"{self.last_price:.2f}")
            else:
                self.live_banner.setText("--")
        else:
            self.live_banner.setText("FLAT")

    # -------------------- Update & Rendering (end)

    # -------------------- Proximity / Heat transitions (start)
    def _update_proximity_alerts(self):
        # Stop proximity already handled in _update_target_stop_cells;
        # here we only emit logs on transitions to reduce noise.
        if self.stop_price is None or self.last_price is None:
            return
        near = abs(self.last_price - self.stop_price) <= 1.0
        prev_key = "_stop_near_prev"
        was_near = getattr(self, prev_key, None)
        if was_near is None or was_near != near:
            setattr(self, prev_key, near)
            if near:
                log.warning("[panel2] Stop proximity detected — flashing active")
            else:
                log.info("[panel2] Stop proximity cleared — flashing off")

    def _update_heat_state_transitions(self, _prev_last: Optional[float], new_last: Optional[float]):
        if self.entry_price is None or getattr(self, "entry_qty", 0) == 0 or self.is_long is None or new_last is None:
            return
        in_drawdown = (new_last < self.entry_price) if self.is_long else (new_last > self.entry_price)
        prev_drawdown = None
        key = "_prev_drawdown_state"
        if hasattr(self, key):
            prev_drawdown = getattr(self, key)
        setattr(self, key, in_drawdown)

        if prev_drawdown is None:
            return  # first sample

        if prev_drawdown != in_drawdown:
            if in_drawdown:
                log.info("[panel2] Heat state: drawdown entered")
            else:
                log.info("[panel2] Heat state: drawdown exited")

    # -------------------- Proximity / Heat transitions (end)

    # -------------------- Public API (compatibility) --------------------
    def refresh(self) -> None:
        """Public refresh method to align with tests and other panels."""
        try:
            self._refresh_all_cells()
        except Exception:
            pass

    # -------------------- Panel 3 data access interface (start)
    def get_current_trade_data(self) -> dict:
        """
        Expose current trade metrics for Panel 3 to grab directly.
        Returns all live trading data including P&L, MAE, MFE, R-multiple, etc.
        Panel 3 uses this for real-time statistical analysis before storage.
        """
        data = {
            "symbol": self.symbol,
            "entry_qty": self.entry_qty,
            "entry_price": self.entry_price,
            "is_long": self.is_long,
            "target_price": self.target_price,
            "stop_price": self.stop_price,
            "last_price": self.last_price,
            "session_high": self.session_high,
            "session_low": self.session_low,
            "vwap": self.vwap,
            "cum_delta": self.cum_delta,
            "entry_time_epoch": self.entry_time_epoch,
            "heat_start_epoch": self.heat_start_epoch,
            "trade_min_price": self._trade_min_price,
            "trade_max_price": self._trade_max_price,
        }

        # Calculate derived metrics if we have an active position
        if self.entry_qty and self.entry_price is not None and self.last_price is not None:
            # P&L calculation
            sign = 1 if self.is_long else -1
            pnl_pts = (self.last_price - self.entry_price) * sign
            gross_pnl = pnl_pts * DOLLARS_PER_POINT * self.entry_qty
            comm = COMM_PER_CONTRACT * self.entry_qty
            net_pnl = gross_pnl - comm

            data["pnl_points"] = pnl_pts
            data["gross_pnl"] = gross_pnl
            data["commissions"] = comm
            data["net_pnl"] = net_pnl

            # MAE/MFE from TRADE extremes (not session extremes)
            # LONG: MAE from min (adverse), MFE from max (favorable)
            # SHORT: MAE from max (adverse), MFE from min (favorable)
            # These track min/max SINCE position entry, not session-wide
            if self._trade_min_price is not None and self._trade_max_price is not None:
                if self.is_long:
                    mae_pts = min(0.0, self._trade_min_price - self.entry_price)
                    mfe_pts = max(0.0, self._trade_max_price - self.entry_price)
                else:  # SHORT
                    mae_pts = min(0.0, self.entry_price - self._trade_max_price)
                    mfe_pts = max(0.0, self.entry_price - self._trade_min_price)

                data["mae_points"] = mae_pts
                data["mfe_points"] = mfe_pts
                data["mae_dollars"] = mae_pts * DOLLARS_PER_POINT * self.entry_qty
                data["mfe_dollars"] = mfe_pts * DOLLARS_PER_POINT * self.entry_qty

                # Calculate efficiency: (realized PnL / MFE) if MFE > 0
                if mfe_pts > 0 and "net_pnl" in data:
                    # Efficiency = realized profit / maximum potential profit
                    # Expressed as percentage (0.0 to 1.0, where 1.0 = 100% efficient)
                    efficiency = min(1.0, max(0.0, data["net_pnl"] / (mfe_pts * DOLLARS_PER_POINT * self.entry_qty)))
                    data["efficiency"] = efficiency
                else:
                    data["efficiency"] = None

            # R-multiple
            if self.stop_price is not None and float(self.stop_price) > 0:
                risk_per_contract = abs(self.entry_price - float(self.stop_price)) * DOLLARS_PER_POINT
                if risk_per_contract > 0:
                    r_multiple = net_pnl / (risk_per_contract * self.entry_qty)
                    data["r_multiple"] = r_multiple

            # Duration
            if self.entry_time_epoch:
                data["duration_seconds"] = int(time.time() - self.entry_time_epoch)

            # Heat duration
            if self.heat_start_epoch:
                data["heat_seconds"] = int(time.time() - self.heat_start_epoch)

        return data

    def get_live_feed_data(self) -> dict:
        """
        Expose current CSV feed data for Panel 3 analysis.
        Returns live market data: price, high, low, vwap, delta.
        """
        return {
            "last_price": self.last_price,
            "session_high": self.session_high,
            "session_low": self.session_low,
            "vwap": self.vwap,
            "cum_delta": self.cum_delta,
        }

    def get_trade_state(self) -> dict:
        """
        Expose position state for Panel 3 queries.
        Returns basic position information: qty, entry, direction, targets.
        """
        return {
            "symbol": self.symbol,
            "qty": self.entry_qty,
            "entry_price": self.entry_price,
            "is_long": self.is_long,
            "target_price": self.target_price,
            "stop_price": self.stop_price,
            "has_position": bool(self.entry_qty and self.entry_qty > 0),
        }

    def has_active_position(self) -> bool:
        """Quick check if there's an active trade for Panel 3 to analyze."""
        return bool(self.entry_qty and self.entry_qty > 0 and self.entry_price is not None)

    # -------------------- Panel 3 data access interface (end)

    # -------------------- Public convenience: seed test data (optional) (start)
    def seed_demo_position(
        self,
        qty: int = 2,
        entry: float = 4000.00,
        is_long: bool = True,
        target: float | None = None,
        stop: float | None = None,
    ):
        """Optional helper for quick manual testing."""
        self.set_position(qty, entry, is_long)
        self.set_targets(target, stop)

    # -------------------- Public convenience: seed test data (optional) (end)

    # -------------------- Theme refresh (start) -----------------------------------
    def _build_theme_stylesheet(self) -> str:
        """Build Panel2 stylesheet."""
        return f"QWidget#Panel2 {{ background:{THEME.get('bg_panel')}; }}"

    def _get_theme_children(self) -> list:
        """Return child widgets to refresh."""
        cells = [
            self.c_price,
            self.c_heat,
            self.c_time,
            self.c_target,
            self.c_stop,
            self.c_risk,
            self.c_rmult,
            self.c_range,
            self.c_mae,
            self.c_mfe,
            self.c_vwap,
            self.c_delta,
            self.c_poc,
            self.c_eff,
            self.c_pts,
        ]
        if hasattr(self, "pills") and self.pills:
            cells.append(self.pills)
        return cells

    def _on_theme_refresh(self) -> None:
        """Update banners after theme refresh."""
        # Update banners
        if hasattr(self, "symbol_banner") and self.symbol_banner:
            self.symbol_banner.setStyleSheet(f"color: {THEME.get('ink')};")
        if hasattr(self, "live_banner") and self.live_banner:
            self.live_banner.setStyleSheet(f"color: {THEME.get('ink')};")

    # -------------------- Theme refresh (end) -------------------------------------

    # Ensure timers persisted on close
    def closeEvent(self, ev: QtGui.QCloseEvent) -> None:
        self._save_state()
        super().closeEvent(ev)


# -------------------- Panel 2 Main (end)
