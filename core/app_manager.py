from __future__ import annotations

import contextlib

# File: core/app_manager.py
# Block: full-module (Part 1/1)
# Purpose: MainWindow orchestration, vertical panel stack, theme routing, DTC init & guarded logon
import os

from PyQt6 import QtCore, QtWidgets

from config.settings import DEBUG_DATA, DTC_HOST, DTC_PORT, LIVE_ACCOUNT
from config.theme import THEME, ColorTheme, set_theme  # noqa: F401  # theme tokens used by helpers
from core.data_bridge import DTCClientJSON
from core.message_router import MessageRouter
from panels.panel1 import Panel1
from panels.panel2 import Panel2
from panels.panel3 import Panel3
from utils.logger import get_logger


# -------------------- Module logger (start)
log = get_logger("AppManager")
if os.getenv("DEBUG_DTC", "0") == "1":
    print("DEBUG: app_manager.py module loaded, logger initialized")
try:
    if os.getenv("DEBUG_DTC", "0") == "1":
        log.debug("[Startup] app_manager module loaded")
except Exception as e:
    if os.getenv("DEBUG_DTC", "0") == "1":
        print(f"DEBUG: Logger TEST FAILED at module level: {e}")
        import traceback
        traceback.print_exc()
# -------------------- Module logger (end)


# -------------------- MainWindow (start)
class MainWindow(QtWidgets.QMainWindow):
    """Main application window tying together all three panels, theme logic, and DTC wiring."""

    themeChanged = QtCore.pyqtSignal(str)  # emits "DEBUG" | "SIM" | "LIVE"

    def __init__(self) -> None:
        super().__init__()
        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: MainWindow.__init__ STARTING")
        try:
            log.info("[startup] Initializing MainWindow")
        except Exception as e:
            if os.getenv("DEBUG_DTC", "0") == "1":
                print(f"DEBUG: Logger FAILED: {e}")
                import traceback
                traceback.print_exc()

        # Initialize state and UI
        self._setup_window()
        self._setup_state_manager()
        self._setup_theme()
        self._build_ui()
        self._setup_theme_toolbar()
        self._setup_mode_selector()
        self._setup_reset_balance_hotkey()

        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: MainWindow.__init__ COMPLETE")
        try:
            log.info("[startup] MainWindow initialized")
        except Exception:
            pass

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("APPSIERRA")
        self.setMinimumSize(1100, 720)

    def _setup_state_manager(self) -> None:
        """Initialize state manager with error handling."""
        try:
            # Initialize database tables first
            print("[DEBUG app_manager._setup_state_manager] Initializing database...")
            from data.db_engine import init_db
            init_db()
            print("[DEBUG app_manager._setup_state_manager] Database initialized successfully")

            from core.state_manager import StateManager
            from core.app_state import set_state_manager

            self._state = StateManager()

            # Register globally for access throughout the app
            set_state_manager(self._state)

            # Load SIM balance from database (sum of all trades' realized P&L)
            print("[DEBUG app_manager._setup_state_manager] Loading SIM balance from trades...")
            loaded_balance = self._state.load_sim_balance_from_trades()
            print(f"\n[INITIAL BALANCE] SIM Account Loaded")
            print(f"  Starting Balance: $10,000.00")
            print(f"  Loaded Balance: ${self._state.sim_balance:,.2f}")
            print(f"  Total P&L from Trades: ${self._state.sim_balance - 10000.0:+,.2f}\n")
            print(f"[DEBUG app_manager._setup_state_manager] SIM balance loaded: ${self._state.sim_balance:,.2f} (returned: ${loaded_balance:,.2f})")
        except Exception as e:
            error_msg = str(e).replace('\u2705', '[OK]').replace('\u2717', '[FAIL]').replace('✓', '[OK]').replace('✗', '[FAIL]')
            print(f"[DEBUG app_manager._setup_state_manager] Error: {error_msg}")
            print(f"[DEBUG app_manager._setup_state_manager] EXCEPTION TYPE: {type(e).__name__}")
            print(f"[DEBUG app_manager._setup_state_manager] FULL TRACEBACK:")
            import traceback
            traceback.print_exc()
            self._state = None

    def _setup_theme(self) -> None:
        """Configure theme system and apply initial theme."""
        self.current_theme_mode: str = "LIVE"  # default to LIVE mode
        # Startup guards
        self._post_construct_invoked: bool = False
        self._dtc_started: bool = False
        self.themeChanged.connect(self.on_theme_changed)
        # Suppress timeframe handling during startup init
        self._startup_done: bool = False
        # Apply base theme BEFORE building widgets to avoid initial flicker
        try:
            from config.theme import switch_theme

            switch_theme(self.current_theme_mode.lower())
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.setFont(
                    ColorTheme.qfont(
                        int(THEME.get("ui_font_weight")),
                        int(THEME.get("ui_font_size")),
                    )
                )
        except Exception:
            pass

    def _build_ui(self) -> None:
        """Build UI panels and initialize DTC connection."""
        # Vertical stacking: Panel1 (balance/investing), Panel2 (live), Panel3 (stats)
        central = QtWidgets.QWidget(self)
        central.setObjectName("CentralWidget")
        # Set main background color from theme
        central.setStyleSheet(f"QWidget#CentralWidget {{ background: {THEME.get('bg_primary')}; }}")
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: About to create panels (Panel1, Panel2, Panel3)...")
        self.panel_balance: Panel1 = Panel1()
        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: Panel1 created")
        self.panel_live: Panel2 = Panel2()
        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: Panel2 created")
        self.panel_stats: Panel3 = Panel3()
        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: Panel3 created")
            log.debug("[Startup] Panels created: Panel1/Panel2/Panel3")

        # Start DTC and diagnostics immediately
        if os.getenv("DEBUG_DTC", "0") == "1":
            print("DEBUG: About to initialize DTC and run diagnostics...")
        try:
            if not getattr(self, "_dtc_started", False):
                if os.getenv("DEBUG_DTC", "0") == "1":
                    log.debug("[Startup] Direct DTC init + diagnostics (panel-init path)")
                    print("DEBUG: Calling _init_dtc()...")
                self._init_dtc()
                if os.getenv("DEBUG_DTC", "0") == "1":
                    print("DEBUG: Calling _run_diagnostics_and_push()...")
                self._run_diagnostics_and_push()
                if os.getenv("DEBUG_DTC", "0") == "1":
                    print("DEBUG: DTC init and diagnostics completed")
        except Exception as e:
            log.exception(f"[Startup] Direct init after panel build failed: {e}")
            if os.getenv("DEBUG_DTC", "0") == "1":
                print(f"DEBUG: DTC init FAILED: {e}")
                import traceback
                traceback.print_exc()
        finally:
            # Enable timeframe signals after startup work completes
            self._startup_done = True
            if os.getenv("DEBUG_DTC", "0") == "1":
                print("DEBUG: Startup done flag set to True")

        # Initialize timeframe pill color to current PnL direction
        with contextlib.suppress(Exception):
            self._sync_pills_color_from_panel1()

        # Setup cross-panel communication and layout stacking
        self._setup_cross_panel_linkage(outer)
        # Reassert intended theme after panel construction, in case any panel
        # applied its own global theme during __init__.
        try:
            self.on_theme_changed(self.current_theme_mode)
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug(f"[Theme] Reapplied {self.current_theme_mode.upper()} after panel init")
        except Exception:
            pass

        # Initialize Panel1's session start balance and equity curve
        # This ensures PnL calculates from the session start, not from the first balance update
        print(f"[DEBUG app_manager._build_ui] STEP 1: Checking panel_balance={self.panel_balance}, _state={self._state}")
        try:
            if self.panel_balance and self._state:
                print(f"[DEBUG app_manager._build_ui] STEP 2: Both panel_balance and _state exist")
                starting_balance = self._state.sim_balance
                print(f"[DEBUG app_manager._build_ui] STEP 3: starting_balance = {starting_balance}")

                # CRITICAL: Load equity curve from database FIRST (before adding any new points)
                # This ensures we don't lose historical data
                print(f"[DEBUG app_manager._build_ui] STEP 3a: Loading equity curve from database for SIM/''")
                self.panel_balance._equity_points = self.panel_balance._get_equity_curve("SIM", "")
                print(f"[DEBUG app_manager._build_ui] STEP 3b: Loaded {len(self.panel_balance._equity_points)} points from database")

                # If we loaded historical data, don't add a new starting point (use the last balance from history)
                # Only add initial point if this is a fresh start with no trades
                if not self.panel_balance._equity_points:
                    print(f"[DEBUG app_manager._build_ui] STEP 3c: No historical data, adding initial point")
                    # Store the session start balance for PnL baseline calculation
                    self.panel_balance._session_start_balance_sim = starting_balance
                    self.panel_balance._session_start_balance_live = 0.0  # No LIVE balance at startup
                    # Also add it to equity curve so graph has initial point
                    self.panel_balance.update_equity_series_from_balance(starting_balance, mode="SIM")
                else:
                    print(f"[DEBUG app_manager._build_ui] STEP 3c: Historical data found, using last balance as session start")
                    # Use the last point from historical data as session start baseline
                    last_balance = self.panel_balance._equity_points[-1][1]
                    self.panel_balance._session_start_balance_sim = last_balance
                    self.panel_balance._session_start_balance_live = 0.0  # No LIVE balance at startup
                    print(f"[DEBUG app_manager._build_ui] Session start balance set to ${last_balance:,.2f} (from last trade)")

                # Display SIM balance by emitting balance signal
                print(f"[DEBUG app_manager._build_ui] STEP 4: Emitting balance signal for SIM balance display...")
                try:
                    # Emit the balance signal directly to trigger display
                    self._state.balanceChanged.emit(starting_balance)
                    print(f"[DEBUG app_manager._build_ui] STEP 4d: SIM balance signal emitted: ${starting_balance:,.2f}")
                except Exception as e:
                    print(f"[DEBUG app_manager._build_ui] Error emitting balance signal: {e}")

                # Redraw graph with loaded equity curve
                print(f"[DEBUG app_manager._build_ui] STEP 3d: Replotting graph with loaded curve")
                if hasattr(self.panel_balance, "_replot_from_cache"):
                    self.panel_balance._replot_from_cache()

                print(f"\n[SESSION START] Panel 1 Initialized")
                print(f"  Session Start Balance (SIM): ${starting_balance:,.2f}")
                print(f"  Equity Curve Points: {len(self.panel_balance._equity_points)}")
                print(f"  PnL Baseline Set: ${self.panel_balance._session_start_balance_sim:,.2f}\n")
                print(f"[DEBUG app_manager._build_ui] Initialized Panel1 with SIM balance: ${starting_balance:,.2f}")
                print(f"[DEBUG app_manager._build_ui] Session start balance SIM: ${self.panel_balance._session_start_balance_sim:,.2f}")
                log.debug(f"[Startup] Panel1 initialized with SIM balance: ${starting_balance:,.2f}")
            else:
                print(f"[DEBUG app_manager._build_ui] STEP 2z: panel_balance or _state is None/False")
        except Exception as e:
            print(f"[DEBUG app_manager._build_ui] EXCEPTION: Failed to initialize Panel1: {e}")
            import traceback
            traceback.print_exc()
            log.debug(f"[Startup] Failed to initialize Panel1: {e}")

    def _setup_cross_panel_linkage(self, outer: QtWidgets.QVBoxLayout) -> None:
        """
        Wire cross-panel communication and add panels to layout.

        Establishes signal connections between Panel1, Panel2, and Panel3,
        routes DTC signals, and stacks panels in the main layout.
        """
        # Single source of truth for timeframe
        self.current_tf: str = "LIVE"

        # Link Panel1 <-> Panel3 (existing)
        if hasattr(self.panel_balance, "set_stats_panel"):
            self.panel_balance.set_stats_panel(self.panel_stats)

        # Link Panel3 -> Panel2 for direct data access
        # Panel 3 grabs live trade data from Panel 2 for statistical analysis
        if hasattr(self.panel_stats, "set_live_panel"):
            self.panel_stats.set_live_panel(self.panel_live)
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[Startup] Wired Panel3 -> Panel2 (direct data access)")

        # Stats panel timeframe -> central handler
        if hasattr(self.panel_stats, "timeframeChanged"):
            try:
                self.panel_stats.timeframeChanged.connect(
                    self._on_stats_tf_changed,
                    type=QtCore.Qt.ConnectionType.UniqueConnection,
                )
                if os.getenv("DEBUG_DTC", "0") == "1":
                    log.debug("[Startup] Wired Panel3 timeframe -> _on_stats_tf_changed")
            except Exception:
                pass

        # Panel2 pills timeframe -> central handler
        try:
            pills = getattr(self.panel_live, "pills", None)
            if pills is not None and hasattr(pills, "timeframeChanged"):
                pills.timeframeChanged.connect(
                    self._on_live_pills_tf_changed,
                    type=QtCore.Qt.ConnectionType.UniqueConnection,
                )
                if os.getenv("DEBUG_DTC", "0") == "1":
                    log.debug("[Startup] Wired Panel2 pills timeframe -> _on_live_pills_tf_changed")
        except Exception:
            pass

        # Refresh Panel 3 stats when Panel 2 reports a closed trade
        # Also trigger Panel 3 to grab data from Panel 2 for analysis
        try:
            if hasattr(self.panel_live, "tradesChanged"):

                def _on_trade_changed(payload):
                    pnl = payload.get("realized_pnl", 0)
                    symbol = payload.get("symbol", "?")

                    # Call Panel 3 trade closed handler
                    if hasattr(self.panel_stats, "on_trade_closed"):
                        try:
                            self.panel_stats.on_trade_closed(payload)
                        except Exception as e:
                            pass

                    # Refresh historical stats from database (redundant but safe)
                    if hasattr(self.panel_stats, "_load_metrics_for_timeframe"):
                        try:
                            self.panel_stats._load_metrics_for_timeframe(self.panel_stats._tf)
                        except Exception as e:
                            pass

                    # Grab live data from Panel 2 and analyze
                    if hasattr(self.panel_stats, "analyze_and_store_trade_snapshot"):
                        try:
                            self.panel_stats.analyze_and_store_trade_snapshot()
                        except Exception as e:
                            pass

                self.panel_live.tradesChanged.connect(_on_trade_changed)
                log.debug("[Startup] Wired Panel2 tradesChanged -> Panel3 (metrics + live analysis)")
        except Exception as e:
            import traceback
            traceback.print_exc()

        # -------------------- DTC Signal Routing (Removed) --------------------
        # NOTE: DTC signal routing (signal_order, signal_position, signal_balance) has been
        # moved to MessageRouter for centralized handling. MessageRouter auto-subscribes to
        # Blinker signals and handles:
        #   - Order routing to Panel2
        #   - Position routing to Panel2
        #   - Balance routing to Panel1
        #   - Auto-detection of trading mode (LIVE/SIM)
        #   - Balance refresh requests after order fills
        #   - Qt thread marshaling for UI updates
        #
        # See: core/message_router.py::_subscribe_to_signals() and signal handlers
        # Benefits: Single source of truth, uses helper modules (qt_bridge, trade_mode),
        #           eliminates duplicate code and reduces complexity.
        # -----------------------------------------------------------------------

        # Layout stacking and relative stretch (make all panels equal height)
        outer.addWidget(self.panel_balance, 1)
        outer.addWidget(self.panel_live, 1)
        outer.addWidget(self.panel_stats, 1)

    def _setup_theme_toolbar(self) -> None:
        """Setup theme switcher toolbar (ENV-gated)."""
        try:
            show_toolbar = str(os.getenv("APPSIERRA_SHOW_THEME_TOOLBAR", "0")).strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            if show_toolbar:
                tb = QtWidgets.QToolBar("Mode", self)
                tb.setMovable(False)
                self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, tb)

                act_debug = QtWidgets.QAction("DEBUG", self)
                act_sim = QtWidgets.QAction("SIM", self)
                act_live = QtWidgets.QAction("LIVE", self)

                act_debug.triggered.connect(lambda: self._set_theme_mode("DEBUG"))
                act_sim.triggered.connect(lambda: self._set_theme_mode("SIM"))
                act_live.triggered.connect(lambda: self._set_theme_mode("LIVE"))

                tb.addAction(act_debug)
                tb.addAction(act_sim)
                tb.addAction(act_live)

                # Optional: Optimize Archives action (manual trigger for SQLite VACUUM)
                try:
                    act_opt = QtWidgets.QAction("Optimize Archives", self)
                    act_opt.triggered.connect(self._optimize_archives_ui)
                    tb.addSeparator()
                    tb.addAction(act_opt)
                except Exception:
                    pass
        except Exception:
            pass

    def _setup_mode_selector(self) -> None:
        """Setup mode selector hotkey (Ctrl+Shift+M)."""
        try:
            from utils.mode_selector import setup_mode_hotkey

            setup_mode_hotkey(self)
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[Startup] Mode selector hotkey (Ctrl+Shift+M) enabled")
        except Exception as e:
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.warning(f"[Startup] Could not setup mode hotkey: {e}")

    def _setup_reset_balance_hotkey(self) -> None:
        """Setup SIM balance reset hotkey (Ctrl+Shift+R)."""
        try:
            from PyQt6.QtWidgets import QShortcut
            from PyQt6.QtGui import QKeySequence

            shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
            shortcut.activated.connect(self._on_reset_sim_balance_hotkey)
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[Startup] Reset balance hotkey (Ctrl+Shift+R) enabled")
        except Exception as e:
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.warning(f"[Startup] Could not setup reset balance hotkey: {e}")

    def _on_reset_sim_balance_hotkey(self) -> None:
        """
        Handler for Ctrl+Shift+R - Reset SIM balance to $10K.
        Called when user presses the hotkey.
        """
        try:
            from core.state_manager import StateManager
            from core.sim_balance import get_sim_balance_manager

            # Reset SIM balance in both places
            if self._state:
                new_balance = self._state.reset_sim_balance_to_10k()
            else:
                # Fallback to sim_balance manager
                mgr = get_sim_balance_manager()
                new_balance = mgr.reset_balance()

            # Update Panel1 display
            if self.panel_balance:
                self.panel_balance.set_account_balance(new_balance)
                self.panel_balance.update_equity_series_from_balance(new_balance, mode="SIM")

            log.info(f"[Hotkey] SIM balance reset to ${new_balance:,.2f}")

            # Show user feedback
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "SIM Balance Reset",
                    f"SIM balance has been reset to ${new_balance:,.2f}"
                )
            except Exception:
                pass

        except Exception as e:
            log.error(f"[Hotkey] Error resetting SIM balance: {e}", exc_info=True)

    # -------------------- Theme handler (start)
    def _set_theme_mode(self, mode: str) -> None:
        """
        Switch theme mode (called by toolbar buttons or hotkey).
        Sets the theme, emits signal, and updates central widget background.

        Args:
            mode: One of "DEBUG", "SIM", or "LIVE"
        """
        try:
            if mode not in ("DEBUG", "SIM", "LIVE"):
                return
            # Switch the THEME dictionary
            from config.theme import switch_theme

            switch_theme(mode.lower())
            # Emit signal to trigger on_theme_changed
            self.themeChanged.emit(mode)
            # Update central widget background
            central = self.centralWidget()
            if central:
                central.setStyleSheet(f"QWidget#CentralWidget {{ background: {THEME.get('bg_primary')}; }}")
        except Exception:
            pass

    def on_theme_changed(self, mode: str) -> None:
        """
        Respond to theme mode changes ("DEBUG" / "SIM" / "LIVE").
        Refreshes all panels and UI elements to match new theme.

        Args:
            mode: One of "DEBUG", "SIM", or "LIVE"
        """
        try:
            if mode not in ("DEBUG", "SIM", "LIVE"):
                return
            self.current_theme_mode = mode

            # Refresh connection icon
            icon = getattr(self.panel_balance, "conn_icon", None)
            if icon and hasattr(icon, "refresh_theme"):
                icon.refresh_theme()

            # Refresh Panel 1 (balance/investing)
            if hasattr(self.panel_balance, "_refresh_theme_colors"):
                self.panel_balance._refresh_theme_colors()

            # Refresh Panel 2 (live)
            if hasattr(self.panel_live, "refresh_theme"):
                self.panel_live.refresh_theme()

            # Refresh Panel 3 (stats)
            if hasattr(self.panel_stats, "refresh_theme"):
                self.panel_stats.refresh_theme()

            # Update central widget background
            central = self.centralWidget()
            if central:
                central.setStyleSheet(f"QWidget#CentralWidget {{ background: {THEME.get('bg_primary')}; }}")
        except Exception:
            pass

    # -------------------- Theme handler (end)

    def _optimize_archives_ui(self) -> None:
        """Manual trigger to VACUUM SQLite archive databases.
        Scans the working directory and 'data/' for *.db files.
        """
        try:
            from utils.archive_maintenance import optimize_archives_with_prompt
        except Exception:
            return
        try:
            root = os.getcwd()
            # Prefer data/ if present, else cwd
            data_dir = os.path.join(root, "data")
            scan_root = data_dir if os.path.isdir(data_dir) else root
            optimize_archives_with_prompt(scan_root, threshold_mb=200.0, parent=self)
        except Exception:
            pass

    # -------------------- Timeframe wiring (start)
    def _on_tf_changed(self, tf: str) -> None:
        """
        Central timeframe handler: called by Panel2 pills and Panel3 stats.
        Validates TF, persists state, and fans out updates to panels.
        """
        try:
            if tf not in ("LIVE", "1D", "1W", "1M", "3M", "YTD"):
                return
            self.current_tf = tf

            # Panel1 drives the graph windowing & endpoint recolor
            if hasattr(self, "panel_balance"):
                self.panel_balance.set_timeframe(tf)

            # Optional: if Panel2 needs to react locally to TF, forward it
            if hasattr(self, "panel_live") and hasattr(self.panel_live, "set_timeframe"):
                with contextlib.suppress(Exception):
                    self.panel_live.set_timeframe(tf)  # harmless if no-op

            # Keep LIVE-dot visibility/pulsing correct in Panel2
            try:
                if hasattr(self.panel_live, "set_live_dot_visible"):
                    self.panel_live.set_live_dot_visible(tf == "LIVE")
                if hasattr(self.panel_live, "set_live_dot_pulsing"):
                    self.panel_live.set_live_dot_pulsing(tf == "LIVE")
            except Exception:
                pass

            # Also refresh the pill highlight color from current PnL direction
            self._sync_pills_color_from_panel1()

        except Exception:
            pass

    # -------------------- Timeframe wiring (end)

    # -------------------- Legacy timeframe hook (start)
    def _on_timeframe_changed(self, tf: str) -> None:
        """Back-compat delegate used by older signal hookups."""
        self._on_live_pills_tf_changed(tf)

    # -------------------- Legacy timeframe hook (end)

    def _on_live_pills_tf_changed(self, tf: str) -> None:
        """Panel 2 timeframe pills changed: update ONLY Panel 1 timeframe."""
        try:
            if not getattr(self, "_startup_done", False):
                return
            if tf not in ("LIVE", "1D", "1W", "1M", "3M", "YTD"):
                return
            self.current_tf = tf
            if hasattr(self, "panel_balance"):
                self.panel_balance.set_timeframe(tf)
            # Visual sync for pills color based on Panel1 PnL direction
            self._sync_pills_color_from_panel1()
        except Exception:
            pass

    def _on_stats_tf_changed(self, tf: str) -> None:
        """Stats (Panel 3) timeframe changed: do not propagate globally."""
        try:
            if not getattr(self, "_startup_done", False):
                return
            if tf not in ("1D", "1W", "1M", "3M", "YTD"):
                return
            # Panel 3 handles its own cells; no global actions here.
            return
        except Exception:
            pass

    # -------------------- PnL?Pills sync (start)
    def _pnl_color_from_direction(self, up: object) -> str:
        """
        Derive a HEX color for PnL direction:
          up is True  -> positive (green)
          up is False -> negative (red)
          up is None  -> neutral
        Pulls from THEME if available; otherwise uses safe defaults.
        """
        try:
            pos = THEME.get("pnl_pos_color", "#22C55E")
            neg = THEME.get("pnl_neg_color", "#EF4444")
            neu = THEME.get("pnl_neu_color", "#9CA3AF")
            if up is True:
                return str(pos)
            if up is False:
                return str(neg)
            return str(neu)
        except Exception:
            return "#C8CDD3"

    def _sync_pills_color_from_panel1(self) -> None:
        """
        Read Panel1's current PnL direction and apply it to the active pill color.
        Safe if pills or _pnl_up aren't present.
        """
        try:
            # Derive pill color from Panel1 current PnL direction
            up = getattr(self.panel_balance, "_pnl_up", None)
            color = self._pnl_color_from_direction(up)
            pills2 = getattr(self.panel_live, "pills", None)
            if pills2 and hasattr(pills2, "set_active_color"):
                pills2.set_active_color(color)
            # Leave Panel 3 (stats) to color its own pills based on its timeframe PnL
        except Exception:
            pass

    # -------------------- PnL?Pills sync (end)
    # -------------------- DTC startup (consolidated) --------------------
    def _init_dtc(self) -> None:
        """Initialize DTC client and start connection immediately (guarded)."""
        try:
            if getattr(self, "_dtc_started", False):
                if os.getenv("DEBUG_DTC", "0") == "1":
                    log.debug("[DTC] Init already started; skipping duplicate init")
                return
            host = DTC_HOST
            port = int(DTC_PORT)
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug(f"[DTC] Searching for DTC server at {host}:{port}")

            # Create message router to dispatch data to panels and state
            # Note: MessageRouter will auto-subscribe to Blinker signals
            router = MessageRouter(
                state=self._state,
                panel_balance=self.panel_balance,
                panel_live=self.panel_live,
                panel_stats=self.panel_stats,
                dtc_client=None,  # Will be set after DTC client is created
                auto_subscribe=True,  # Subscribe to Blinker signals
            )
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[DTC] MessageRouter instantiated and wired to panels/state")

            self._dtc = DTCClientJSON(host=host, port=port, router=router)

            # Give router access to DTC client for balance refresh requests
            router._dtc_client = self._dtc
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[DTC] Router now has DTC client reference for balance requests")

            self._connect_dtc_signals()

            # Request balance after session is ready
            if hasattr(self._dtc, "session_ready"):

                def _on_session_ready():
                    log.info("[startup] DTC session ready")
                    if os.getenv("DEBUG_DTC", "0") == "1":
                        print("DEBUG: Session ready - balance will be requested by data_bridge")

                self._dtc.session_ready.connect(_on_session_ready)
                if os.getenv("DEBUG_DTC", "0") == "1":
                    log.debug("[Startup] Wired session_ready -> request_account_balance")

            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("[DTC] Client constructed; initiating TCP connect")
            if hasattr(self._dtc, "connect") and callable(self._dtc.connect):
                self._dtc_started = True
                self._dtc.connect()
        except Exception as e:
            log.exception(f"[DTC] Init failed: {e}")

    def _connect_dtc_signals(self) -> None:
        """Wire DTC client signals to UI + logs (guarded for presence)."""
        try:
            if not getattr(self, "_dtc", None):
                return
            c = self._dtc
            if hasattr(c, "connected"):
                c.connected.connect(self._on_dtc_connected)
            if hasattr(c, "disconnected"):
                c.disconnected.connect(self._on_dtc_disconnected)
            if hasattr(c, "errorOccurred"):
                c.errorOccurred.connect(self._on_dtc_error)
            if hasattr(c, "message"):
                c.message.connect(self._on_dtc_message)
            if hasattr(c, "messageReceived"):
                c.messageReceived.connect(self._on_dtc_message)
        except Exception:
            pass

    def _run_diagnostics_and_push(self) -> None:
        """Run optional startup diagnostics (no longer updates connection icon)."""
        # Diagnostics no longer update connection icon (dual-circle uses timing-based logic)
        try:
            from core.startup_diagnostics import run_diagnostics

            run_diagnostics()  # Still run diagnostics for logging/monitoring
        except Exception:
            pass

    # -------------------- DTC signal bridges --------------------
    def _on_dtc_connected(self) -> None:
        """Called when DTC connection is established (updates outer ring)."""
        log.info("[info] DTC connected")
        icon = getattr(self.panel_balance, "conn_icon", None)
        if icon and hasattr(icon, "mark_connected"):
            icon.mark_connected()

    def _on_dtc_disconnected(self) -> None:
        """Called when DTC connection is lost (clears all timers)."""
        log.info("[info] DTC disconnected")
        icon = getattr(self.panel_balance, "conn_icon", None)
        if icon and hasattr(icon, "mark_disconnected"):
            icon.mark_disconnected()

    def _on_dtc_error(self, msg: str) -> None:
        """Called on DTC error (no explicit action needed - heartbeat timeout will trigger yellow/red)."""
        log.error(f"[error] DTC error: {msg}")
        # No explicit action needed - the connection dot will automatically
        # transition to yellow/red based on heartbeat timeout

    def _on_dtc_message(self, msg: dict) -> None:
        """Called when any DTC message is received (updates both rings)."""
        icon = getattr(self.panel_balance, "conn_icon", None)
        if icon:
            # Check if this is a heartbeat message (Type 3)
            if msg.get("Type") == 3 and hasattr(icon, "mark_heartbeat"):
                icon.mark_heartbeat()
            # All messages count as data activity
            if hasattr(icon, "mark_data_activity"):
                icon.mark_data_activity()

    def closeEvent(self, event) -> None:
        """Called when the app is closing. Log final balance state."""
        try:
            if self._state:
                final_balance = self._state.sim_balance
                print(f"\n{'='*80}")
                print(f"[APP CLOSING] Final Balance Check")
                print(f"{'='*80}")
                print(f"  Final SIM Balance: ${final_balance:,.2f}")
                print(f"  Starting Balance: $10,000.00")
                print(f"  Session P&L: ${final_balance - 10000.0:+,.2f}")
                print(f"  Status: {'PERSISTENT [OK]' if final_balance != 10000.0 else 'Default (no trades)'}")
                print(f"{'='*80}\n")
                log.info(f"[Shutdown] App closing with SIM balance: ${final_balance:,.2f}")
        except Exception as e:
            print(f"[ERROR] Failed to log closing state: {e}")

        super().closeEvent(event)


# -------------------- MainWindow (end)
