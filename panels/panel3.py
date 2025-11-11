# File: panels/panel3.py
# Block: full-module (Part 1/1)
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6 import QtCore, QtWidgets

from config.theme import THEME, ColorTheme
from utils.theme_mixin import ThemeAwareMixin
from utils.ui_helpers import centered_row


# --- Externalized metric set (with safe fallback) ----------------------------
try:
    from config.trading_specs import PANEL3_METRICS  # type: ignore
except Exception:
    PANEL3_METRICS = [
        "Total PnL",
        "Max Drawdown",
        "Max Run-Up",
        "Expectancy",
        "Avg Time",
        "Trades",
        "Best",
        "Worst",
        "Hit Rate",
        "Commissions",
        "Avg R",
        "Profit Factor",
        "Streak",
        "MAE",
        "MFE",
    ]

import contextlib

from widgets.metric_grid import MetricGrid  # type: ignore
from widgets.sharpe_bar import SharpeBarWidget  # type: ignore

# --- Timeframe pills (shared implementation) ---------------------------------
from widgets.timeframe_pills import TradingStatsTimeframePills  # type: ignore


# =============================================================================
# Panel 3 — Trading Stats
# =============================================================================
class Panel3(QtWidgets.QWidget, ThemeAwareMixin):
    """
    Panel 3 — TRADING STATS
    • Centered title
    • Centered timeframe pills (1D, 1W, 1M, 3M, YTD)
    • MetricGrid (cols=5) fed by update_metrics(...)
    • Sharpe ratio bar at bottom
    """

    timeframeChanged = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._tf: str = "1D"
        self._panel_live = None  # Reference to Panel 2 for direct data access
        self._build_ui()
        # Initial load
        with contextlib.suppress(Exception):
            self._load_metrics_for_timeframe(self._tf)

        # Connect to mode changes so we reload metrics when switching SIM/LIVE
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            if state and hasattr(state, 'modeChanged'):
                state.modeChanged.connect(self._on_mode_changed)
                print(f"[DEBUG panel3.__init__] Connected to modeChanged signal")
        except Exception as e:
            print(f"[DEBUG panel3.__init__] Failed to connect mode signal: {e}")

        # Apply current theme colors (in case theme was switched before this panel was created)
        self.refresh_theme()

    # -------------------- UI BUILD -------------------------------------------

    def _build_ui(self) -> None:
        self.setObjectName("Panel3")
        self.setStyleSheet(f"QWidget#Panel3 {{ background:{THEME.get('bg_panel', '#0B0F14')}; }}")

        root = QtWidgets.QVBoxLayout(self)
        # Match Panel 2 margins/spacing
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        # Title (centered) - uses heading font (Lato in LIVE/SIM)
        self.lbl_title = QtWidgets.QLabel("TRADING STATS")
        self.lbl_title.setStyleSheet(
            f"color:{THEME.get('ink')}; "
            f"{ColorTheme.heading_font_css(int(THEME.get('title_font_weight')), int(THEME.get('title_font_size')))}; "
            "letter-spacing:0.6px;"
        )
        root.addLayout(centered_row(self.lbl_title))

        # Timeframe pills (centered row)
        self.tf_pills = TradingStatsTimeframePills()
        if hasattr(self.tf_pills, "timeframeChanged"):
            self.tf_pills.timeframeChanged.connect(self._on_tf_changed)
        # Leave active color to app manager sync (based on PnL direction)
        pills_row = QtWidgets.QHBoxLayout()
        pills_row.setContentsMargins(0, 0, 0, 0)
        pills_row.setSpacing(0)
        pills_row.addStretch(1)
        pills_row.addWidget(self.tf_pills, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        pills_row.addStretch(1)
        root.addLayout(pills_row)

        # Metrics grid (3x5 like Panel 2)
        self.metric_grid = MetricGrid(PANEL3_METRICS, cols=5)
        root.addWidget(self.metric_grid)

        # Sharpe ratio bar at bottom
        self.sharpe_bar = SharpeBarWidget()
        root.addWidget(self.sharpe_bar)

    # -------------------- Timeframe ------------------------------------------
    def set_timeframe(self, tf: str) -> None:
        if tf not in ("1D", "1W", "1M", "3M", "YTD"):
            return
        self._tf = tf
        self.timeframeChanged.emit(tf)
        # Refresh metrics for this panel only
        with contextlib.suppress(Exception):
            self._load_metrics_for_timeframe(tf)

    def _on_tf_changed(self, tf: str) -> None:
        self.set_timeframe(tf)

    def _on_mode_changed(self, mode: str) -> None:
        """Called when trading mode switches (SIM <-> LIVE)"""
        print(f"[DEBUG panel3._on_mode_changed] Mode changed to {mode}, reloading metrics")
        with contextlib.suppress(Exception):
            self._load_metrics_for_timeframe(self._tf)

    def refresh_pill_colors(self) -> None:
        """
        Force timeframe pills to refresh their colors from THEME.
        Called when trading mode switches (DEBUG/SIM/LIVE) to update pill colors.
        """
        try:
            if hasattr(self.tf_pills, "set_active_color"):
                # Clear cached color to force refresh
                if hasattr(self.tf_pills, "_last_active_hex"):
                    delattr(self.tf_pills, "_last_active_hex")
                # Re-read color from THEME based on Total PnL (done in _load_metrics_for_timeframe)
                # For now, just force a re-application by calling set_active_color with neutral
                from config.theme import ColorTheme

                self.tf_pills.set_active_color(THEME.get("pnl_neu_color", "#9CA3AF"))
        except Exception:
            pass

    # -------------------- Public API -----------------------------------------
    def update_metrics(self, data: dict[str, Any]) -> None:
        """Push a dict of metric name -> value into the grid."""
        for name in PANEL3_METRICS:
            if name in data:
                self.metric_grid.update_metric(name, data[name])

    def refresh(self) -> None:
        with contextlib.suppress(Exception):
            self.update()

    def _build_theme_stylesheet(self) -> str:
        """Build Panel3 stylesheet."""
        return f"QWidget#Panel3 {{ background:{THEME.get('bg_panel')}; }}"

    def _get_theme_children(self) -> list:
        """Return child widgets to refresh."""
        children = []
        if hasattr(self, "tf_pills") and self.tf_pills:
            children.append(self.tf_pills)
        if hasattr(self, "metric_grid") and self.metric_grid:
            children.append(self.metric_grid)
        return children

    def _on_theme_refresh(self) -> None:
        """Update title label after theme refresh."""
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet(
                f"color:{THEME.get('ink')}; "
                f"{ColorTheme.heading_font_css(int(THEME.get('title_font_weight')), int(THEME.get('title_font_size')))}; "
                "letter-spacing:0.6px;"
            )

    # -------------------- Panel 2 Integration (Direct Data Access) ----------
    def set_live_panel(self, panel_live) -> None:
        """
        Wire Panel 2 reference for direct data access.
        Called by app_manager during initialization.
        """
        self._panel_live = panel_live

    def grab_live_trade_data(self) -> Optional[dict[str, Any]]:
        """
        Grab current trade data directly from Panel 2.
        This is the primary data source for real-time statistical analysis.
        Returns None if Panel 2 is not available or no active position.
        """
        if self._panel_live is None:
            return None

        # Check if Panel 2 has an active position
        if not hasattr(self._panel_live, "has_active_position") or not self._panel_live.has_active_position():
            return None

        # Grab comprehensive trade data from Panel 2
        try:
            trade_data = self._panel_live.get_current_trade_data()
            feed_data = self._panel_live.get_live_feed_data()
            state_data = self._panel_live.get_trade_state()

            # Combine all data sources
            combined = {**trade_data, **feed_data, **state_data}
            return combined
        except Exception as e:
            try:
                from utils.logger import get_logger

                log = get_logger(__name__)
                log.warning(f"[panel3] Failed to grab data from Panel 2: {e}")
            except Exception:
                pass
            return None

    def register_order_event(self, payload: dict) -> None:
        """
        Handle normalized OrderUpdate from DTC router.
        Called by message_router when an order update arrives.

        Args:
            payload: Normalized order update dict from message_router
        """
        try:
            # Just log for now - Panel 3 updates via _load_metrics_for_timeframe
            from utils.logger import get_logger

            log = get_logger(__name__)
            order_status = payload.get("OrderStatus")
            if order_status in (3, 7):  # Filled status
                log.debug("[panel3] Order filled detected - will refresh metrics on next timeframe check")
        except Exception:
            pass

    def analyze_and_store_trade_snapshot(self) -> None:
        """
        Grab current trade data from Panel 2, perform statistical analysis,
        then store results for historical analysis.

        This implements the intended data flow:
        Panel 2 -> Panel 3 (grab data) -> Statistical Analysis -> Storage
        """
        # Grab data from Panel 2
        live_data = self.grab_live_trade_data()
        if live_data is None:
            return

        try:
            # TODO: Add statistical analysis here
            # Examples:
            # - Calculate rolling averages
            # - Update drawdown tracking
            # - Compute efficiency metrics
            # - Analyze VWAP relationship
            # - Track delta correlation with P&L

            # For now, log that we grabbed the data
            from utils.logger import get_logger

            log = get_logger(__name__)
            log.info(
                f"[panel3] Grabbed live trade data from Panel 2: "
                f"Symbol={live_data.get('symbol')}, "
                f"PnL=${live_data.get('net_pnl', 0):.2f}, "
                f"R={live_data.get('r_multiple', 'N/A')}"
            )

            # TODO: Store analyzed data to database for historical analysis
            # This would call a new service method like:
            # from services.analysis_store import record_trade_snapshot
            # record_trade_snapshot(live_data, analysis_results)

        except Exception as e:
            try:
                from utils.logger import get_logger

                log = get_logger(__name__)
                log.error(f"[panel3] Error analyzing trade snapshot: {e}")
            except Exception:
                pass

    # -------------------- Data & Metrics (local to Panel 3) -----------------
    def _load_metrics_for_timeframe(self, tf: str) -> None:
        """Query closed trades within timeframe and update metric cells and Sharpe bar.
        Prefers TradeRecord.exit_time; falls back to timestamp if absent.
        Filters by active trading mode (SIM/LIVE).
        """
        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf={tf}")
        try:
            from services.stats_service import compute_trading_stats_for_timeframe
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 2: stats_service imported successfully")
        except Exception as e:
            print(f"[DEBUG panel3._load_metrics_for_timeframe] ERROR importing stats_service: {e}")
            return

        # Get active mode from state manager
        mode = None
        try:
            from core.app_state import get_state_manager
            state = get_state_manager()
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 3: State manager obtained")
            # Use position_mode if there's an active position, otherwise current_mode
            mode = state.position_mode if state and state.has_active_position() else (state.current_mode if state else "SIM")
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 4: Mode detected as {mode}")
        except Exception as e:
            print(f"[DEBUG panel3._load_metrics_for_timeframe] WARNING: Failed to detect mode, using SIM default: {e}")
            mode = "SIM"  # Default fallback

        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 5: Calling compute_trading_stats_for_timeframe with tf={tf}, mode={mode}")
        payload = compute_trading_stats_for_timeframe(tf, mode=mode)
        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 6: compute_trading_stats_for_timeframe returned payload with keys: {list(payload.keys())}")

        # Check if we have any trades for this mode in this timeframe
        trades_count = payload.get("_trade_count", 0)
        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for {mode} mode in {tf}: {trades_count}")
        if trades_count == 0:
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 8: No trades found, calling display_empty_metrics")
            self.display_empty_metrics(mode, tf)
            return

        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics")
        self.update_metrics(payload)
        print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed")

        # Update Sharpe bar widget (Sharpe Ratio not in grid)
        try:
            sr = payload.get("Sharpe Ratio")
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 10: Sharpe Ratio value: {sr}")
            if sr is not None:
                self.sharpe_bar.set_value(float(sr))
                print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 11: Sharpe bar updated")
        except Exception as e:
            print(f"[DEBUG panel3._load_metrics_for_timeframe] WARNING: Failed to update Sharpe bar: {e}")

        # Color the timeframe pills based on total PnL sign
        try:
            total_val = float(payload.get("_total_pnl_value", 0.0))
            print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 12: Total PnL value: {total_val}")
            up = True if total_val > 0 else False if total_val < 0 else None
            active_color = ColorTheme.pnl_color_from_direction(up)
            if hasattr(self.tf_pills, "set_active_color"):
                self.tf_pills.set_active_color(active_color)
                print(f"[DEBUG panel3._load_metrics_for_timeframe] STEP 13: Timeframe pills color updated")
        except Exception as e:
            print(f"[DEBUG panel3._load_metrics_for_timeframe] WARNING: Failed to update pill colors: {e}")

    def display_empty_metrics(self, mode: str, tf: str) -> None:
        """Display empty state when no trades exist for mode in timeframe."""
        try:
            # Set all metrics to "--" or "N/A"
            empty_data = {
                "Total PnL": "$0.00",
                "Max Drawdown": "$0.00",
                "Max Run-Up": "$0.00",
                "Expectancy": "$0.00",
                "Avg Time": "--",
                "Trades": "0",
                "Best": "$0.00",
                "Worst": "$0.00",
                "Hit Rate": "0.0%",
                "Commissions": "$0.00",
                "Avg R": "0.00R",
                "Profit Factor": "--",
                "Streak": "--",
                "MAE": "$0.00",
                "MFE": "$0.00",
            }
            self.update_metrics(empty_data)

            # Reset Sharpe bar
            if hasattr(self, "sharpe_bar") and self.sharpe_bar:
                self.sharpe_bar.set_value(0.0)

            # Set pills to neutral color
            try:
                if hasattr(self.tf_pills, "set_active_color"):
                    self.tf_pills.set_active_color(THEME.get("pnl_neu_color", "#9CA3AF"))
            except Exception:
                pass

        except Exception as e:
            try:
                from utils.logger import get_logger
                log = get_logger(__name__)
                log.error(f"[panel3] Error displaying empty metrics: {e}")
            except Exception:
                pass

    def on_trade_closed(self, trade_payload: dict) -> None:
        """Called when Panel 2 reports a closed trade.
        Refreshes statistics to show updated metrics.
        """
        print(f"[DEBUG panel3.on_trade_closed] STEP 1: Trade closed notification received: {trade_payload}")
        try:
            from utils.logger import get_logger
            log = get_logger(__name__)
            print(f"[DEBUG panel3.on_trade_closed] STEP 2: Logger obtained")

            # Refresh the metrics for current timeframe
            print(f"[DEBUG panel3.on_trade_closed] STEP 3: Calling _load_metrics_for_timeframe with tf={self._tf}")
            self._load_metrics_for_timeframe(self._tf)
            print(f"[DEBUG panel3.on_trade_closed] STEP 4: _load_metrics_for_timeframe returned")

            # Grab live data from Panel 2 if available
            if hasattr(self, "analyze_and_store_trade_snapshot"):
                print(f"[DEBUG panel3.on_trade_closed] STEP 5: Calling analyze_and_store_trade_snapshot")
                self.analyze_and_store_trade_snapshot()
                print(f"[DEBUG panel3.on_trade_closed] STEP 6: analyze_and_store_trade_snapshot returned")
            else:
                print(f"[DEBUG panel3.on_trade_closed] WARNING: analyze_and_store_trade_snapshot method not found")

            print(f"[DEBUG panel3.on_trade_closed] STEP 7: Trade close handling completed successfully")
            log.debug(f"[panel3] Metrics refreshed on trade close")
        except Exception as e:
            print(f"[DEBUG panel3.on_trade_closed] ERROR: {e}")
            try:
                from utils.logger import get_logger
                log = get_logger(__name__)
                log.error(f"[panel3] Error handling trade close: {e}")
            except Exception:
                pass
