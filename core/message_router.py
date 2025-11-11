from __future__ import annotations

import contextlib
import os

# File: core/message_router.py
# Unified message router between DTC client and GUI panels.
from typing import Any, Dict, Optional

import structlog

from core.state_manager import StateManager
from panels.panel1 import Panel1
from panels.panel2 import Panel2
from panels.panel3 import Panel3
from services.trade_service import TradeManager
from utils.debug_flags import debug_data, debug_signal
from utils.qt_bridge import marshal_to_qt_thread
from utils.trade_mode import auto_detect_mode_from_order, auto_detect_mode_from_position, log_mode_switch


log = structlog.get_logger(__name__)


class MessageRouter:
    """
    Central dispatcher for normalized DTC AppMessages.

    The router receives messages from data_bridge.DTCClientJSON
    and fans them out to the correct GUI panel or subsystem.
    """

    def __init__(
        self,
        state: Optional[StateManager] = None,
        panels: Optional[dict[str, Any]] = None,
        panel_balance: Optional[Panel1] = None,
        panel_live: Optional[Panel2] = None,
        panel_stats: Optional[Panel3] = None,
        dtc_client: Optional[Any] = None,
        auto_subscribe: bool = True,
    ):
        # Core wiring
        self.state = state
        self._dtc_client = dtc_client

        # Support both legacy direct panels and new dict-style panels
        if panels:
            self.panel_balance = panels.get("balance") or panel_balance
            self.panel_live = panels.get("live") or panel_live
            self.panel_stats = panels.get("stats") or panel_stats
        else:
            self.panel_balance = panel_balance
            self.panel_live = panel_live
            self.panel_stats = panel_stats

        # Initialize unified trade manager for historical data
        self._trade_manager = TradeManager()

        # Map of event -> handler
        self._handlers = {
            "TRADE_ACCOUNT": self._on_trade_account,
            "BALANCE_UPDATE": self._on_balance_update,
            "POSITION_UPDATE": self._on_position_update,
            "ORDER_UPDATE": self._on_order_update,
            # Optional extensions:
            "MARKET_TRADE": self._on_market_trade,
            "MARKET_BIDASK": self._on_market_bidask,
        }

        # Mode tracking for drift detection
        self._current_mode: str = "DEBUG"
        self._current_account: str = ""

        # Coalesced UI updates (10Hz refresh rate)
        self._ui_refresh_pending: bool = False
        self._ui_refresh_timer: Optional[Any] = None
        self.UI_REFRESH_INTERVAL_MS: int = 100  # 10 Hz

        # Subscribe to Blinker signals for direct DTC event routing
        if auto_subscribe:
            self._subscribe_to_signals()
            if os.getenv("DEBUG_DTC", "0") == "1":
                log.debug("router.signals.subscribed", msg="Subscribed to Blinker signals")

    # -------------------- Mode Drift Sentinel --------------------
    def _check_mode_drift(self, msg: dict[str, Any]) -> None:
        """
        Check if incoming message's TradeAccount disagrees with active (mode, account).
        Non-blocking: logs structured event and could show yellow banner.

        Args:
            msg: DTC message with TradeAccount field
        """
        incoming_account = msg.get("TradeAccount", "")
        if not incoming_account:
            return

        from datetime import datetime, timezone
        from utils.trade_mode import detect_mode_from_account

        incoming_mode = detect_mode_from_account(incoming_account)

        # Check for drift
        if (incoming_mode, incoming_account) != (self._current_mode, self._current_account):
            # Log structured event
            log.warning(
                "MODE_DRIFT_DETECTED",
                expected_mode=self._current_mode,
                expected_account=self._current_account,
                incoming_mode=incoming_mode,
                incoming_account=incoming_account,
                message_type=msg.get("Type"),
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

            # Could show yellow banner here (future enhancement)
            # self._show_mode_drift_banner(incoming_mode, incoming_account)

    # -------------------- Coalesced UI Updates --------------------
    def _schedule_ui_refresh(self) -> None:
        """
        Schedule a coalesced UI refresh.
        UI updates are batched and executed at 10Hz to prevent flicker.
        """
        if self._ui_refresh_pending:
            return

        self._ui_refresh_pending = True

        # Use QTimer if available (Qt environment)
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(self.UI_REFRESH_INTERVAL_MS, self._flush_ui_updates)
        except Exception:
            # Fallback: immediate flush if Qt not available
            self._flush_ui_updates()

    def _flush_ui_updates(self) -> None:
        """
        Execute accumulated UI updates in a single batch.
        Called after coalescing interval expires.
        """
        self._ui_refresh_pending = False

        try:
            # Update all panels in single batch
            if self.panel_balance and hasattr(self.panel_balance, "update"):
                self.panel_balance.update()

            if self.panel_live and hasattr(self.panel_live, "update"):
                self.panel_live.update()

            if self.panel_stats and hasattr(self.panel_stats, "update"):
                self.panel_stats.update()

        except Exception as e:
            log.warning(f"router.ui_flush_error: {str(e)}")

    # -------------------- Signal subscription (Blinker) --------------------
    def _subscribe_to_signals(self) -> None:
        """
        Subscribe to Blinker signals for direct DTC event routing.
        This replaces the manual signal wiring in app_manager.py.
        """
        try:
            from core.data_bridge import (
                signal_balance,
                signal_order,
                signal_position,
                signal_trade_account,
            )

            # Subscribe to each signal with weak=False to prevent premature cleanup
            signal_order.connect(self._on_order_signal, weak=False)
            signal_position.connect(self._on_position_signal, weak=False)
            signal_balance.connect(self._on_balance_signal, weak=False)
            signal_trade_account.connect(self._on_trade_account_signal, weak=False)

            debug_signal("MessageRouter subscribed to all Blinker signals")

        except Exception as e:
            log.error(f"router.signals.subscribe_failed: {str(e)}")
            import traceback

            traceback.print_exc()

    # -------------------- Signal handlers (Blinker -> Qt thread bridge) --------------------
    def _on_order_signal(self, sender, **kwargs) -> None:
        """Handle ORDER_UPDATE Blinker signal."""
        try:
            # Blinker sends payload as 'sender' argument
            msg = sender if isinstance(sender, dict) else kwargs

            try:
                debug_signal(f"ORDER signal received: {msg.get('Symbol', 'N/A')}", throttle_ms=1000)
            except:
                pass  # Debug logging failure shouldn't break routing

            # Check for mode drift
            self._check_mode_drift(msg)

            # Check mode precedence and auto-detect trading mode
            try:
                from utils.trade_mode import should_switch_mode_debounced, detect_mode_from_account

                account = msg.get("TradeAccount", "")
                if account:
                    # Use debounced mode switch check
                    if should_switch_mode_debounced(account, self._current_mode):
                        detected_mode = detect_mode_from_account(account)

                        # Check if mode switch is allowed
                        if self.state and not self._check_mode_precedence(detected_mode):
                            log.warning(f"router.order.blocked: mode={detected_mode}, reason=Mode blocked by open position")
                            return

                        # Broadcast mode change to all panels
                        if self.panel_balance and hasattr(self.panel_balance, "set_trading_mode"):
                            marshal_to_qt_thread(self.panel_balance.set_trading_mode, detected_mode, account)

                        if self.panel_live and hasattr(self.panel_live, "set_trading_mode"):
                            marshal_to_qt_thread(self.panel_live.set_trading_mode, detected_mode, account)

                        if self.panel_stats and hasattr(self.panel_stats, "set_trading_mode"):
                            marshal_to_qt_thread(self.panel_stats.set_trading_mode, detected_mode, account)

                        # Update router's current mode/account
                        self._current_mode = detected_mode
                        self._current_account = account

                        log_mode_switch(self._current_mode, detected_mode, account, log)
            except Exception as e:
                log.warning(f"router.order.mode_detect_failed: {str(e)}")

            # Route to panels via Qt thread
            if self.panel_live and hasattr(self.panel_live, "on_order_update"):
                try:
                    marshal_to_qt_thread(self.panel_live.on_order_update, msg)
                except Exception as e:
                    # Fallback: try direct call if Qt marshaling fails
                    log.warning(f"router.order.marshal_failed: {str(e)}")
                    try:
                        self.panel_live.on_order_update(msg)
                    except Exception as e2:
                        log.error(f"router.order.direct_call_failed: {str(e2)}")

            # Request balance after order is filled (status 3=filled, 7=filled)
            try:
                status = msg.get("OrderStatus")
                if status in (3, 7):
                    # Enhanced order summary log
                    symbol = msg.get("Symbol", "N/A")
                    avg_fill = msg.get("AverageFillPrice") or msg.get("Price1")
                    filled_qty = msg.get("FilledQuantity", 0)
                    buy_sell = "BUY" if msg.get("BuySell") == 1 else "SELL"

                    log.info(
                        f"[ORDER] {symbol} {buy_sell} {filled_qty} @ {avg_fill:.2f} — Filled",
                        status=status,
                    )

                    # Balance updates are only requested at startup, not on every order fill
            except Exception as e:
                log.warning(f"router.order.processing_failed: {str(e)}")

        except Exception as e:
            log.error(f"router.order.handler_failed: {str(e)}")
            import traceback

            traceback.print_exc()

    def _on_position_signal(self, sender, **kwargs) -> None:
        """Handle POSITION_UPDATE Blinker signal."""
        try:
            # Blinker sends payload as 'sender' argument
            msg = sender if isinstance(sender, dict) else kwargs

            try:
                debug_signal(f"POSITION signal received: {msg.get('symbol', 'N/A')}", throttle_ms=1000)
            except:
                pass  # Debug logging failure shouldn't break routing

            # Check for mode drift
            self._check_mode_drift(msg)

            # Auto-detect trading mode ONLY for non-zero positions
            qty = msg.get("qty", msg.get("PositionQuantity", 0))
            if qty != 0:
                try:
                    from utils.trade_mode import should_switch_mode_debounced, detect_mode_from_account

                    account = msg.get("TradeAccount", "")
                    if account:
                        # Use debounced mode switch check
                        if should_switch_mode_debounced(account, self._current_mode, qty):
                            detected_mode = detect_mode_from_account(account)

                            # Check if mode switch is allowed
                            if self.state and not self._check_mode_precedence(detected_mode):
                                log.warning(f"router.position.blocked: mode={detected_mode}, reason=Mode blocked by open position")
                                return

                            # Broadcast mode change to all panels
                            if self.panel_balance and hasattr(self.panel_balance, "set_trading_mode"):
                                marshal_to_qt_thread(self.panel_balance.set_trading_mode, detected_mode, account)

                            if self.panel_live and hasattr(self.panel_live, "set_trading_mode"):
                                marshal_to_qt_thread(self.panel_live.set_trading_mode, detected_mode, account)

                            if self.panel_stats and hasattr(self.panel_stats, "set_trading_mode"):
                                marshal_to_qt_thread(self.panel_stats.set_trading_mode, detected_mode, account)

                            # Update router's current mode/account
                            self._current_mode = detected_mode
                            self._current_account = account

                            log_mode_switch(self._current_mode, detected_mode, account, log)
                except Exception as e:
                    log.warning(f"router.position.mode_detect_failed: {str(e)}")

            # Route to panels via Qt thread
            if self.panel_live and hasattr(self.panel_live, "on_position_update"):
                try:
                    marshal_to_qt_thread(self.panel_live.on_position_update, msg)
                except Exception as e:
                    # Fallback: try direct call if Qt marshaling fails
                    log.warning(f"router.position.marshal_failed: {str(e)}")
                    try:
                        self.panel_live.on_position_update(msg)
                    except Exception as e2:
                        log.error(f"router.position.direct_call_failed: {str(e2)}")

        except Exception as e:
            log.error(f"router.position.handler_failed: {str(e)}")
            import traceback

            traceback.print_exc()

    def _on_balance_signal(self, sender, **kwargs) -> None:
        """Handle BALANCE_UPDATE Blinker signal."""
        try:
            # Blinker sends payload as 'sender' argument
            msg = sender if isinstance(sender, dict) else kwargs

            print(f"\n[DEBUG MESSAGE_ROUTER] BALANCE_UPDATE signal received!")
            print(f"  Full message: {msg}")

            try:
                debug_signal(f"BALANCE signal received: {msg.get('balance', 'N/A')}", throttle_ms=2000)
            except:
                pass  # Debug logging failure shouldn't break routing

            # Extract balance value and account from dict
            balance_value = msg.get("balance") or msg.get("CashBalance") or msg.get("AccountValue")
            account = msg.get("account") or msg.get("TradeAccount") or ""

            print(f"[DEBUG MESSAGE_ROUTER] Extracted values:")
            print(f"  balance_value={balance_value}")
            print(f"  account={account}")

            if balance_value is not None:
                # Detect mode from account
                from utils.trade_mode import detect_mode_from_account
                mode = detect_mode_from_account(account) if account else "SIM"

                print(f"[DEBUG MESSAGE_ROUTER] Detected mode from balance: {mode}, account={account}")

                # NOTE: Do NOT switch mode on balance updates!
                # Mode only switches when actual ORDERS/TRADES come in
                # Balance updates are stored but don't trigger mode changes

                # CRITICAL FIX: Skip DTC balance updates for SIM mode!
                # SIM mode should only use PnL-calculated balance, not DTC broker balance
                if mode == "SIM":
                    print(f"[DEBUG MESSAGE_ROUTER] [OK] SKIPPING balance update for SIM mode")
                    print(f"  Reason: SIM mode uses calculated PnL, not DTC broker balance")
                    print(f"  DTC value ignored: ${float(balance_value):,.2f}\n")
                    return

                # Update state manager with mode-specific balance (LIVE mode only)
                if self.state:
                    old_balance = self.state.get_balance_for_mode(mode)
                    print(f"[DEBUG MESSAGE_ROUTER] Updating balance for LIVE mode")
                    print(f"  Old balance: ${old_balance:,.2f}")
                    print(f"  New balance: ${float(balance_value):,.2f}\n")
                    try:
                        self.state.set_balance_for_mode(mode, float(balance_value))
                        log.debug(f"router.balance.updated: mode={mode}, balance={balance_value}")
                    except Exception as e:
                        log.warning(f"router.balance.state_update_failed: {str(e)}")

                # Update panel UI if this is the active mode
                if self.panel_balance and self.state and mode == self.state.current_mode:
                    try:
                        # CRITICAL: Marshal UI update to main Qt thread
                        marshal_to_qt_thread(self._update_balance_ui, balance_value, mode)
                    except Exception as e:
                        # Fallback: try direct call if Qt marshaling fails
                        log.warning(f"router.balance.marshal_failed: {str(e)}")
                        try:
                            self._update_balance_ui(balance_value, mode)
                        except Exception as e2:
                            log.error(f"router.balance.direct_call_failed: {str(e2)}")

        except Exception as e:
            log.error(f"router.balance.handler_failed: {str(e)}")
            import traceback

            traceback.print_exc()

    def _on_trade_account_signal(self, sender, **kwargs) -> None:
        """Handle TRADE_ACCOUNT Blinker signal."""
        # Blinker sends payload as 'sender' argument
        msg = sender if isinstance(sender, dict) else kwargs

        debug_signal(f"TRADE_ACCOUNT signal received: {msg.get('account', 'N/A')}")

        # Route via existing handler
        self._on_trade_account(msg)

    def _update_balance_ui(self, balance_value: float, mode: Optional[str] = None) -> None:
        """
        Update balance UI - called in main Qt thread via marshal_to_qt_thread.
        Updates both the display label and the equity curve with mode awareness.

        CRITICAL: Only updates if balance is for the current mode!
        """
        try:
            if self.panel_balance and self.state:
                # ONLY update if balance is for the CURRENT mode
                if mode and mode != self.state.current_mode:
                    log.debug(f"router.balance.ignored - balance is for {mode}, current mode is {self.state.current_mode}")
                    return

                if hasattr(self.panel_balance, "set_account_balance"):
                    self.panel_balance.set_account_balance(balance_value)
                if hasattr(self.panel_balance, "update_equity_series_from_balance"):
                    self.panel_balance.update_equity_series_from_balance(balance_value, mode=mode)
        except Exception as e:
            log.error(f"router.balance.ui_update_error: {str(e)}")
            import traceback

            traceback.print_exc()

    # -------------------- main entry --------------------
    def route(self, msg: dict[str, Any]) -> None:
        """
        Main entrypoint for all normalized AppMessages.
        msg = {"type": "BALANCE_UPDATE", "payload": {...}}
        """
        mtype = msg.get("type")
        payload = msg.get("payload", {})
        if not mtype:
            log.debug("router.ignore.empty_type")
            return

        handler = self._handlers.get(mtype)
        if handler:
            try:
                handler(payload)
            except Exception as e:
                log.warning(f"router.handler.error: type={mtype}, error={str(e)}")
        else:
            log.debug(f"router.unhandled: type={mtype}")

    # -------------------- handlers --------------------
    def _on_trade_account(self, payload: dict):
        acct = payload.get("account")

        # Only log account enumeration in debug mode
        if os.getenv("DEBUG_DTC", "0") == "1":
            log.debug(f"router.trade_account.{acct}")

        # Update trade logger with current account
        if self._trade_manager:
            self._trade_manager.set_account(acct)

        if self.panel_balance:
            with contextlib.suppress(Exception):
                self.panel_balance.set_account(acct)
        # Optional helper flag for the rest of the app
        if self.state:
            self.state.current_account = acct
            self.state.is_sim_mode = acct.lower().startswith("sim") if acct else False

        # update theme (DEBUG/SIM/LIVE themes) via MainWindow if needed
        if self.state:
            self.state.current_account = acct

    def _on_balance_update(self, payload: dict):
        bal = payload.get("balance")
        account = payload.get("account") or payload.get("TradeAccount") or ""
        log.debug(f"router.balance: balance={bal}")

        # Detect mode from account
        mode = None
        if account:
            from utils.trade_mode import detect_mode_from_account
            mode = detect_mode_from_account(account)

        # Update state manager (store all balances)
        if self.state:
            self.state.update_balance(bal)
            if mode:
                self.state.set_balance_for_mode(mode, float(bal))

        # CRITICAL: Only update UI if balance is for current mode!
        if self.panel_balance and self.state:
            # Only display if this balance is for the CURRENT mode
            if mode and mode != self.state.current_mode:
                log.debug(f"router.balance.ui_ignored - balance for {mode}, current is {self.state.current_mode}")
                return

            try:
                self.panel_balance.set_account_balance(bal)
                self.panel_balance.update_equity_series_from_balance(bal, mode=mode)
            except Exception:
                pass

    def _on_position_update(self, payload: dict):
        sym = payload.get("symbol")
        qty = payload.get("qty", 0)
        avg = payload.get("avg_entry")

        # CRITICAL: Only process OPEN positions (qty != 0)
        # Ignore zero-quantity positions from initial sync or position closures
        if qty == 0:
            log.debug(f"router.position.closed: symbol={sym}")
            # Remove from state if it exists
            if self.state:
                self.state.update_position(sym, 0, None)
            return

        # ADDITIONAL CHECK: Validate position has required data (avoid stale positions)
        # Sierra sometimes reports positions without proper price data
        if avg is None or avg == 0.0:
            log.warning(
                "router.position.stale",
                symbol=sym,
                qty=qty,
                avg_entry=avg,
                reason="Missing or zero average price - likely stale/ghost position",
            )
            return

        # PHANTOM POSITION FILTER: Skip known phantom positions from Sierra's historical data
        # These are positions that Sierra reports as open but are actually closed
        # Format: symbol -> (qty, avg_price) tuple - if both match, it's phantom
        PHANTOM_POSITIONS = {
            "F.US.MESM25": (1, 5996.5),
        }
        if sym in PHANTOM_POSITIONS:
            phantom_qty, phantom_avg = PHANTOM_POSITIONS[sym]
            if qty == phantom_qty and avg == phantom_avg:
                log.warning(
                    "router.position.phantom",
                    symbol=sym,
                    qty=qty,
                    avg_entry=avg,
                    reason="Matches known phantom position in Sierra - ignoring",
                )
                return

        # Log and process open positions only
        log.debug(f"router.position: symbol={sym}, qty={qty}, avg_entry={avg}")

        # Send to Panel2 (live trading panel) with full payload
        if self.panel_live:
            with contextlib.suppress(Exception):
                self.panel_live.on_position_update(payload)

        # Log to trade logger for historical tracking
        if self._trade_manager:
            with contextlib.suppress(Exception):
                self._trade_manager.on_position_update(payload)

        # Store in state manager
        if self.state:
            self.state.update_position(sym, qty, avg)

    def _on_order_update(self, payload: dict):
        print(f"[DEBUG router._on_order_update] ORDER_UPDATE received: {payload}")
        log.debug("router.order", payload_preview=str(payload)[:120])

        # CRITICAL: Detect and update mode from order's account
        account = payload.get("TradeAccount", "")
        if account:
            from utils.trade_mode import detect_mode_from_account
            order_mode = detect_mode_from_account(account)
            print(f"[DEBUG router._on_order_update] Order from account {account}, mode={order_mode}")

            if self.state and order_mode != self.state.current_mode:
                old_mode = self.state.current_mode
                self.state.current_mode = order_mode
                print(f"[DEBUG router._on_order_update] MODE CHANGED: {old_mode} -> {order_mode}")
                try:
                    self.state.modeChanged.emit(order_mode)
                    print(f"[DEBUG router._on_order_update] modeChanged signal emitted")
                except Exception as e:
                    print(f"[DEBUG router._on_order_update] Error emitting mode signal: {e}")

        # Send to Panel2 (live trading panel) for real-time fill handling
        if self.panel_live:
            print(f"[DEBUG router._on_order_update] Sending to panel_live.on_order_update")
            with contextlib.suppress(Exception):
                self.panel_live.on_order_update(payload)
            print(f"[DEBUG router._on_order_update] Sent to panel_live successfully")
        else:
            print(f"[DEBUG router._on_order_update] WARNING: panel_live not available")

        # Send to Panel3 (statistics panel) for trade statistics
        if self.panel_stats:
            with contextlib.suppress(Exception):
                self.panel_stats.register_order_event(payload)

        # Store in state manager for persistence and analytics
        if self.state:
            self.state.record_order(payload)

    # -------------------- Mode precedence checking --------------------
    def _check_mode_precedence(self, requested_mode: str) -> bool:
        """
        Check if the requested mode is allowed based on open positions.

        Rules:
        1. LIVE mode always allowed (highest precedence)
        2. SIM mode blocked if LIVE position is open
        3. SIM mode allowed if SIM position is open (same mode)

        Args:
            requested_mode: The mode being requested ("SIM", "LIVE", "DEBUG")

        Returns:
            True if mode switch is allowed, False if blocked
        """
        if not self.state:
            return True  # No state manager, allow all

        # LIVE always takes precedence
        if requested_mode == "LIVE":
            return True

        # Check if mode is blocked
        if self.state.is_mode_blocked(requested_mode):
            return False

        return True

    # -------------------- optional extensions --------------------
    def _on_market_trade(self, payload: dict):
        # Placeholder for market trade feed if needed
        log.debug("router.market_trade", payload_preview=str(payload)[:120])

    def _on_market_bidask(self, payload: dict):
        # Placeholder for bid/ask updates
        log.debug("router.market_bidask", payload_preview=str(payload)[:120])
