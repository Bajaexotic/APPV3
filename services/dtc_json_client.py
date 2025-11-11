# dtc_json_client.py (migrated to advanced debug subsystem)
import argparse
from collections.abc import Callable
import contextlib
import json
import os
import socket
import sys
import threading
import time
import traceback
from typing import Optional

# New debug subsystem
from config import settings
from core.diagnostics import debug, error, info, warn


NULL = b"\x00"

# ---------------- DTC Message Type Constants ----------------
LOGON_REQUEST = 1
LOGON_RESPONSE = 2
HEARTBEAT = 3
LOGOFF = 4
ENCODING_REQUEST = 5
ENCODING_RESPONSE = 6

MARKET_DATA_REQUEST = 101
MARKET_DATA_REJECT = 103
MARKET_DATA_UPDATE_TRADE = 107
MARKET_DATA_UPDATE_BID_ASK = 108
MARKET_DATA_UPDATE_SESSION_OPEN = 120
MARKET_DATA_UPDATE_SESSION_HIGH = 121
MARKET_DATA_UPDATE_SESSION_LOW = 122
MARKET_DATA_UPDATE_SESSION_VOLUME = 123
MARKET_DATA_UPDATE_OPEN_INTEREST = 124

SUBMIT_NEW_SINGLE_ORDER = 300
ORDER_UPDATE = 301
HISTORICAL_ORDER_FILLS_REQUEST = 303
HISTORICAL_ORDER_FILL_RESPONSE = 304
OPEN_ORDERS_REQUEST = 305
POSITION_UPDATE = 306  # â† Actual constant name (was OPEN_ORDERS)
ORDER_FILL_RESPONSE = 307
NEW_ORDER_REQUEST = 308
ORDER_CANCEL_REQUEST = 309
ORDER_CANCEL_REPLACE_REQUEST = 310
ORDER_CANCEL_REJECT = 311
ORDER_REJECT = 312
ORDERS_CANCELLED_NOTIFICATION = 313

TRADE_ACCOUNTS_REQUEST = 400
TRADE_ACCOUNT_RESPONSE = 401
CURRENT_POSITIONS_REQUEST = 500  # â† CRITICAL ADDITION
ACCOUNT_BALANCE_UPDATE = 600
ACCOUNT_BALANCE_REQUEST = 601

HISTORICAL_PRICE_DATA_REQUEST = 700
HISTORICAL_PRICE_DATA_RESPONSE_HEADER = 701
HISTORICAL_PRICE_DATA_RECORD_RESPONSE = 702
HISTORICAL_PRICE_DATA_TICK_RECORD_RESPONSE = 703
HISTORICAL_PRICE_DATA_REJECT = 704

USER_MESSAGE = 800
GENERAL_LOG_MESSAGE = 801
ALERT_MESSAGE = 802

SECDEF_FOR_SYMBOL_REQUEST = "SecurityDefinitionForSymbolRequest"
MARKET_DATA_REQUEST_NAME = "MarketDataRequest"
MARKET_DATA_REJECT_NAME = "MarketDataReject"

# --------------- Debug flags (migrated to settings) ---------------
# Legacy: DTC_TRAP and DEBUG_DTC environment variables
# New: Use settings.DEBUG_NETWORK and settings.DEBUG_DATA
DTC_TRAP = os.getenv("DTC_TRAP", "0") == "1"


def _type_to_str(t):
    if isinstance(t, str):
        return t
    if isinstance(t, int):
        return {
            LOGON_REQUEST: "LogonRequest",
            LOGON_RESPONSE: "LogonResponse",
            HEARTBEAT: "Heartbeat",
            LOGOFF: "Logoff",
            ENCODING_REQUEST: "EncodingRequest",
            ENCODING_RESPONSE: "EncodingResponse",
            MARKET_DATA_REQUEST: "MarketDataRequest",
            MARKET_DATA_REJECT: "MarketDataReject",
            MARKET_DATA_UPDATE_TRADE: "MarketDataUpdateTrade",
            MARKET_DATA_UPDATE_BID_ASK: "MarketDataUpdateBidAsk",
            MARKET_DATA_UPDATE_SESSION_OPEN: "MarketDataUpdateSessionOpen",
            MARKET_DATA_UPDATE_SESSION_HIGH: "MarketDataUpdateSessionHigh",
            MARKET_DATA_UPDATE_SESSION_LOW: "MarketDataUpdateSessionLow",
            MARKET_DATA_UPDATE_SESSION_VOLUME: "MarketDataUpdateSessionVolume",
            MARKET_DATA_UPDATE_OPEN_INTEREST: "MarketDataUpdateOpenInterest",
            OPEN_ORDERS_REQUEST: "OpenOrdersRequest",
            ORDER_UPDATE: "OrderUpdate",
            HISTORICAL_ORDER_FILLS_REQUEST: "HistoricalOrderFillsRequest",
            HISTORICAL_ORDER_FILL_RESPONSE: "HistoricalOrderFillResponse",
            POSITION_UPDATE: "PositionUpdate",
            ORDER_FILL_RESPONSE: "OrderFillResponse",
            NEW_ORDER_REQUEST: "NewOrderRequest",
            ORDER_CANCEL_REQUEST: "OrderCancelRequest",
            ORDER_CANCEL_REPLACE_REQUEST: "OrderCancelReplaceRequest",
            ORDER_CANCEL_REJECT: "OrderCancelReject",
            ORDER_REJECT: "OrderReject",
            ORDERS_CANCELLED_NOTIFICATION: "OrdersCancelledNotification",
            TRADE_ACCOUNTS_REQUEST: "TradeAccountsRequest",
            TRADE_ACCOUNT_RESPONSE: "TradeAccountResponse",
            CURRENT_POSITIONS_REQUEST: "CurrentPositionsRequest",
            ACCOUNT_BALANCE_UPDATE: "AccountBalanceUpdate",
            ACCOUNT_BALANCE_REQUEST: "AccountBalanceRequest",
            HISTORICAL_PRICE_DATA_REQUEST: "HistoricalPriceDataRequest",
            HISTORICAL_PRICE_DATA_RESPONSE_HEADER: "HistoricalPriceDataResponseHeader",
            HISTORICAL_PRICE_DATA_RECORD_RESPONSE: "HistoricalPriceDataRecordResponse",
            HISTORICAL_PRICE_DATA_TICK_RECORD_RESPONSE: "HistoricalPriceDataTickRecordResponse",
            HISTORICAL_PRICE_DATA_REJECT: "HistoricalPriceDataReject",
            USER_MESSAGE: "UserMessage",
            GENERAL_LOG_MESSAGE: "GeneralLogMessage",
            ALERT_MESSAGE: "AlertMessage",
        }.get(t, str(t))
    return "?"


# --------------- Safe-caller wrapper ---------------
def _safe_call(label: str, cb, msg):
    if not cb:
        return
    if not settings.DEBUG_UI:
        cb(msg)
        return
    try:
        cb(msg)
    except Exception as e:
        tname = _type_to_str(msg.get("Type"))
        error("ui", f"UI handler error: {label}", context={"label": label, "message_type": tname, "error": str(e)})


class DTCClientJSON:
    """
    JSON-mode DTC client for Sierra Chart.
    - Null-terminated JSON frames
    - Background RX & heartbeat
    - Probe utilities
    - Structured dispatch to UI callbacks
    """

    def __init__(
        self,
        host: str,
        port: int,
        on_msg: Optional[Callable[[dict], None]] = None,  # legacy raw hook
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        trade_account: Optional[str] = None,
        # Panel/UI sinks
        on_position: Optional[Callable[[dict], None]] = None,
        on_order: Optional[Callable[[dict], None]] = None,
        on_order_fill: Optional[Callable[[dict], None]] = None,
        on_account_balance: Optional[Callable[[dict], None]] = None,
        on_trade_account: Optional[Callable[[dict], None]] = None,
        on_md_trade: Optional[Callable[[dict], None]] = None,
        on_md_bidask: Optional[Callable[[dict], None]] = None,
        on_security_definition: Optional[Callable[[dict], None]] = None,
        on_positions_seed_done: Optional[Callable[[], None]] = None,
        on_orders_seed_done: Optional[Callable[[], None]] = None,
        # NEW: universal raw stream hook (preferred)
        on_any_message: Optional[Callable[[dict], None]] = None,
        # Diagnostics
        enable_diagnostics: bool = False,
        diagnostic_logger=None,  # DTCMessageLogger instance
    ):
        self.host, self.port = host, port
        self.sock: Optional[socket.socket] = None
        self._rx_buf = bytearray()
        self._stop = False

        # Connection & identity
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.trade_account = trade_account

        # Structured sinks
        self.on_position = on_position
        self.on_order = on_order
        self.on_order_fill = on_order_fill
        self.on_account_balance = on_account_balance
        self.on_trade_account = on_trade_account
        self.on_md_trade = on_md_trade
        self.on_md_bidask = on_md_bidask
        self.on_security_definition = on_security_definition
        self.on_positions_seed_done = on_positions_seed_done
        self.on_orders_seed_done = on_orders_seed_done

        # Raw stream hook(s)
        # Prefer on_any_message; fall back to on_msg for backward compatibility.
        self.on_any_message = on_any_message or on_msg
        self.on_msg = on_msg  # kept for callers that still use it explicitly

        # Diagnostics
        self.diagnostic_logger = None
        if enable_diagnostics or settings.DEBUG_DATA:
            if diagnostic_logger:
                self.diagnostic_logger = diagnostic_logger
            else:
                try:
                    from dtc_diagnostics import DTCMessageLogger

                    self.diagnostic_logger = DTCMessageLogger()
                    info(
                        "data", "DTC diagnostic logging enabled", context={"log_path": self.diagnostic_logger.log_path}
                    )
                except ImportError:
                    warn("data", "dtc_diagnostics module not found, diagnostic logging disabled")

        # Threads & sequencing
        self._hb_thread: Optional[threading.Thread] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._req_id = 100

    # ---------------- Connection / IO ----------------

    def connect(self, username: str = "", password: str = ""):
        self._stop = False
        self.sock = socket.create_connection((self.host, self.port), timeout=5.0)
        self.sock.settimeout(1.0)

        if self.on_connected:
            with contextlib.suppress(Exception):
                self.on_connected()

        self._send(
            {
                "Type": LOGON_REQUEST,
                "ProtocolVersion": 8,
                "ClientName": "DTCJsonClient",
                "HeartbeatIntervalInSeconds": 5,
                "Username": username,
                "Password": password,
                "TradeMode": 1,
            }
        )

        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True, name="DTC_RX")
        self._rx_thread.start()
        self._hb_thread = threading.Thread(target=self._hb_loop, daemon=True, name="DTC_HB")
        self._hb_thread.start()

    def close(self):
        self._stop = True
        try:
            if self.sock:
                with contextlib.suppress(Exception):
                    self.sock.shutdown(socket.SHUT_RDWR)
                with contextlib.suppress(Exception):
                    self.sock.close()
        finally:
            self.sock = None
            if self.diagnostic_logger:
                with contextlib.suppress(Exception):
                    self.diagnostic_logger.close()
            if self.on_disconnected:
                with contextlib.suppress(Exception):
                    self.on_disconnected()

    def _send(self, obj: dict):
        if not self.sock:
            if settings.DEBUG_NETWORK:
                error(
                    "network",
                    "No socket connection available",
                    context={"message_type": _type_to_str(obj.get("Type")), "attempted_message": str(obj)[:200]},
                )
            return

        # Pre-send validation and logging
        try:
            msg_type = obj.get("Type", "UNKNOWN")
            msg_name = _type_to_str(msg_type)

            # Validate JSON serialization before sending
            try:
                data = json.dumps(obj, separators=(",", ":")).encode("utf-8") + NULL
            except (TypeError, ValueError) as json_err:
                error(
                    "data",
                    "JSON serialization failed for DTC message",
                    context={"message_type": msg_name, "error": str(json_err), "object_repr": str(obj)[:200]},
                )
                return

            # Debug logging for outgoing requests
            if settings.DEBUG_DATA and msg_type != HEARTBEAT:
                # Log all outgoing messages except heartbeats
                compact = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
                if len(compact) > 300:
                    compact = compact[:300] + "…"
                debug(
                    "data",
                    f"TX → {msg_name}",
                    event_type="DTCSend",
                    context={"message_type": msg_name, "payload": compact},
                )

            # Send the data
            self.sock.sendall(data)

        except OSError as e:
            error(
                "network",
                "Socket error sending DTC message",
                context={"message_type": _type_to_str(obj.get("Type")), "error": str(e), "message": str(obj)[:200]},
            )
        except Exception as e:
            error(
                "network",
                "Unexpected error sending DTC message",
                context={"message_type": _type_to_str(obj.get("Type")), "error": str(e), "message": str(obj)[:200]},
            )

    def _rx_loop(self):
        try:
            while not self._stop and self.sock:
                try:
                    chunk = self.sock.recv(65536)
                    if not chunk:
                        break
                    self._rx_buf.extend(chunk)

                    while True:
                        try:
                            i = self._rx_buf.index(0)
                        except ValueError:
                            break
                        raw = self._rx_buf[:i]
                        del self._rx_buf[: i + 1]
                        if not raw:
                            continue
                        try:
                            msg = json.loads(raw.decode("utf-8"))
                        except Exception as e:
                            if settings.DEBUG_DATA:
                                error(
                                    "data",
                                    "DTC JSON parse failed",
                                    context={"error": str(e), "raw_data_length": len(raw)},
                                )
                            continue

                        try:
                            self._dispatch_for_panels(msg)
                        except Exception as e:
                            # Never let UI wiring kill RX loop
                            if settings.DEBUG_UI:
                                error(
                                    "ui",
                                    "DTC dispatch failed",
                                    context={"error": str(e), "message_type": _type_to_str(msg.get("Type"))},
                                )

                        if self.on_msg:
                            try:
                                self.on_msg(msg)
                            except Exception as e:
                                if settings.DEBUG_CORE:
                                    error(
                                        "core",
                                        "DTC on_msg handler failed",
                                        context={"error": str(e), "message_type": _type_to_str(msg.get("Type"))},
                                    )
                except socket.timeout:
                    continue
        finally:
            self.close()

    def _hb_loop(self):
        while not self._stop and self.sock:
            try:
                self._send({"Type": HEARTBEAT})
                time.sleep(4)
            except Exception:
                break

    # ------------------ Dispatch to UI ------------------
    def _dispatch_for_panels(self, msg: dict):
        tname = _type_to_str(msg.get("Type"))

        # Diagnostic logging (if enabled)
        if self.diagnostic_logger:
            try:
                self.diagnostic_logger.log_message(msg)
            except Exception as e:
                if settings.DEBUG_DATA:
                    error("data", "Diagnostic logger failed", context={"error": str(e), "message_type": tname})

        # Raw message debugging (migrated from DEBUG_DTC)
        if settings.DEBUG_DATA:
            try:
                compact = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
                if len(compact) > 300:
                    compact = compact[:300] + "…"
                debug(
                    "data",
                    f"RX ← {tname}",
                    event_type="DTCReceive",
                    context={"message_type": tname, "payload": compact},
                )
            except Exception as e:
                debug(
                    "data",
                    f"RX ← {tname} (unprintable)",
                    event_type="DTCReceive",
                    context={"message_type": tname, "error": str(e)},
                )

        if tname in ("LogonResponse", "EncodingResponse", "Heartbeat"):
            return

        # Accounts
        if tname in ("TradeAccountResponse", "TradeAccountsResponse"):
            _safe_call("on_trade_account", self.on_trade_account, msg)
            return

        # Balances
        if tname in ("AccountBalanceUpdate", "AccountBalanceResponse"):
            _safe_call("on_account_balance", self.on_account_balance, msg)
            return

        # Positions
        if tname == "PositionUpdate":
            _safe_call("on_position", self.on_position, msg)
            upd_reason = msg.get("UpdateReason", "")
            total = msg.get("TotalNumberMessages", 0) or msg.get("TotalNumMessages", 0)
            num = msg.get("MessageNumber", 0)
            if (
                upd_reason in ("CurrentPositionsRequestResponse", "PositionsRequestResponse")
                and ((total and num and total == num) or msg.get("NoPositions") == 1)
                and self.on_positions_seed_done
            ):
                try:
                    self.on_positions_seed_done()
                except Exception as e:
                    if settings.DEBUG_UI:
                        error("ui", "on_positions_seed_done handler failed", context={"error": str(e)})
            return

        # Orders
        if tname == "OrderUpdate":
            _safe_call("on_order", self.on_order, msg)
            upd_reason = msg.get("UpdateReason", "")
            total = msg.get("TotalNumberMessages", 0) or msg.get("TotalNumMessages", 0)
            num = msg.get("MessageNumber", 0)
            if (
                upd_reason in ("OpenOrdersRequestResponse", "OrdersRequestResponse")
                and ((total and num and total == num) or msg.get("NoOrders") == 1)
                and self.on_orders_seed_done
            ):
                try:
                    self.on_orders_seed_done()
                except Exception as e:
                    if settings.DEBUG_UI:
                        error("ui", "on_orders_seed_done handler failed", context={"error": str(e)})
            return

        # Fills
        if tname in ("OrderFillResponse", "HistoricalOrderFillResponse"):
            _safe_call("on_order_fill", self.on_order_fill, msg)
            return

        # Market data
        if tname in ("MarketDataUpdateTrade", "MarketDataSnapshot", "MarketDataUpdateLastTrade"):
            _safe_call("on_md_trade", self.on_md_trade, msg)
            return
        if tname == "MarketDataUpdateBidAsk":
            _safe_call("on_md_bidask", self.on_md_bidask, msg)
            return

        # Security definition
        if tname in ("SecurityDefinitionResponse", "SecurityDefinitionForSymbolResponse"):
            _safe_call("on_security_definition", self.on_security_definition, msg)
            return
        # else: ignore

    # ------------------ Probe helpers -------------------
    def _next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def probe_server(self):
        print(">> Sending probe requests...\n")

        # ---- Step 1: Request trade accounts
        acct_req_id = self._next_req_id()
        self._send({"Type": TRADE_ACCOUNTS_REQUEST, "RequestID": acct_req_id})
        print(f"  [1/5] Trade Accounts Request (ID={acct_req_id})")
        time.sleep(0.25)

        # ---- Step 2: Request current positions (Type 500)
        pos_req_id = self._next_req_id()
        pos_req = {"Type": CURRENT_POSITIONS_REQUEST, "RequestID": pos_req_id}
        if self.trade_account:
            pos_req["TradeAccount"] = self.trade_account
        self._send(pos_req)
        print(f"  [2/5] Current Positions Request (ID={pos_req_id})")
        time.sleep(0.25)

        # ---- Step 3: Request open orders (Type 305)
        orders_req_id = self._next_req_id()
        orders_req = {"Type": OPEN_ORDERS_REQUEST, "RequestID": orders_req_id}
        if self.trade_account:
            orders_req["TradeAccount"] = self.trade_account
        self._send(orders_req)
        print(f"  [3/5] Open Orders Request (ID={orders_req_id})")
        time.sleep(0.25)

        # ---- Step 4: Request historical fills (Type 303) - CRITICAL FOR PANEL 3
        fills_req_id = self._next_req_id()
        fills_req = {"Type": HISTORICAL_ORDER_FILLS_REQUEST, "RequestID": fills_req_id}
        if self.trade_account:
            fills_req["TradeAccount"] = self.trade_account
        # Request fills from last 30 days (DTC uses DateTime as Unix timestamp)
        fills_req["NumberOfDays"] = 30
        self._send(fills_req)
        print(f"  [4/5] Historical Order Fills Request (ID={fills_req_id}, 30 days)")
        time.sleep(0.25)

        # ---- Optional: subscribe to market data if requested via env
        sym = os.getenv("SIERRA_MD_SYMBOL")
        if sym:
            self._send(
                {
                    "Type": MARKET_DATA_REQUEST,
                    "RequestID": self._next_req_id(),
                    "RequestAction": 1,  # 1 = Subscribe
                    "Symbol": sym,  # e.g. F.US.MESZ25
                    "Exchange": "",
                    "UnsubscribeAll": 0,
                    "SymbolID": 1,
                }
            )
            print(f"[MD SUBSCRIBE] Requested market data for {sym}")

        time.sleep(0.25)

        # ---- Step 5: Request account balance
        bal_req_id = self._next_req_id()
        bal_req = {"Type": ACCOUNT_BALANCE_REQUEST, "RequestID": bal_req_id}
        if self.trade_account:
            bal_req["TradeAccount"] = self.trade_account
        self._send(bal_req)
        print(f"  [5/5] Account Balance Request (ID={bal_req_id})")

        print("\n[OK] All probe requests sent. Listening for responses...\n")
        print("  Enable DEBUG_DTC=1 or DTC_TRAP=1 to see raw message traffic\n")

    def request_historical_fills(self, num_days: int = 30):
        """
        Request historical order fills from Sierra Chart DTC server.
        This is critical for populating Panel 3 (Trading Stats) on startup.

        Args:
            num_days: Number of days of historical fills to request (default 30)
        """
        fills_req_id = self._next_req_id()
        fills_req = {"Type": HISTORICAL_ORDER_FILLS_REQUEST, "RequestID": fills_req_id, "NumberOfDays": num_days}
        if self.trade_account:
            fills_req["TradeAccount"] = self.trade_account

        self._send(fills_req)
        print(f"[FILLS REQUEST] Requesting {num_days} days of historical fills (ID={fills_req_id})")
        return fills_req_id

    def request_account_balance(self, trade_account: Optional[str] = None):
        """
        Request current account balance from Sierra Chart DTC server (Type 601).

        Args:
            trade_account: Optional specific trade account to query. If None, uses self.trade_account

        Returns:
            Request ID for tracking the response
        """
        bal_req_id = self._next_req_id()
        bal_req = {"Type": ACCOUNT_BALANCE_REQUEST, "RequestID": bal_req_id}
        acct = trade_account or self.trade_account
        if acct:
            bal_req["TradeAccount"] = acct
        self._send(bal_req)
        if DTC_TRAP or os.getenv("DEBUG_DTC"):
            print(f"[BAL REQUEST] Account balance request sent (ID={bal_req_id}, Acct={acct or 'ALL'})")
        return bal_req_id

    def request_trade_accounts(self):
        """
        Request list of available trade accounts from Sierra Chart DTC server (Type 400).

        Returns:
            Request ID for tracking the response
        """
        acct_req_id = self._next_req_id()
        self._send({"Type": TRADE_ACCOUNTS_REQUEST, "RequestID": acct_req_id})
        if DTC_TRAP or os.getenv("DEBUG_DTC"):
            print(f"[ACCT REQUEST] Trade accounts list request sent (ID={acct_req_id})")
        return acct_req_id

    def subscribe_symbol(self, symbol: str, exchange: str = ""):
        rid = self._next_req_id()
        self._send(
            {
                "Type": MARKET_DATA_REQUEST_NAME,
                "RequestAction": 1,
                "SymbolID": rid,
                "Symbol": symbol,
                "Exchange": exchange,
            }
        )
        self._send(
            {
                "Type": SECDEF_FOR_SYMBOL_REQUEST,
                "RequestID": rid,
                "Symbol": symbol,
                "Exchange": exchange,
            }
        )


# ------------------ Pretty printer & CLI ------------------
def pretty_print_msg(msg: dict, file_log=None):
    mtype = msg.get("Type")
    tname = _type_to_str(mtype)

    if tname == "LogonResponse":
        print(f"[LOGON OK] {msg.get('ResultText','')}")
        return
    if tname == "Heartbeat":
        return

    if tname in ("TradeAccountResponse", "TradeAccountsResponse"):
        acct = msg.get("TradeAccount", "")
        print(f"[ACCOUNT] TradeAccount={acct}")
    elif tname in ("AccountBalanceUpdate", "AccountBalanceResponse"):
        acct = msg.get("TradeAccount", "")
        cash = msg.get("CashBalance", "")
        nlv = msg.get("AccountValue", msg.get("NetLiquidatingValue", ""))
        avl = msg.get("AvailableFunds", "")
        print(f"[BALANCE] Acct={acct}  Cash={cash}  NLV={nlv}  Avail={avl}")
    elif tname == "PositionUpdate":
        sym = msg.get("Symbol", "")
        qty = msg.get("Quantity", "")
        avg = msg.get("AveragePrice", "")
        upl = msg.get("OpenProfitLoss", "")
        unsolicited = msg.get("Unsolicited", 0)
        flag = "LIVE" if unsolicited else "SNAP"
        print(f"[POSITION {flag}] {sym:12} Qty={qty:>5} Avg={avg:>10}  UPL={upl}")
    elif tname == "OrderUpdate":
        sym = msg.get("Symbol", "")
        side = msg.get("BuySell", "")
        status = msg.get("OrderStatus", "")
        p1 = msg.get("Price1", "")
        filled = msg.get("FilledQuantity", "")
        soid = msg.get("ServerOrderID", "")
        print(f"[ORDER] {side:<1} {sym:12} {status:<12} @ {p1:<10} filled={filled:<6} id={soid}")
    elif tname in ("OrderFillResponse", "HistoricalOrderFillResponse"):
        sym = msg.get("Symbol", "")
        side = msg.get("BuySell", "")
        qty = msg.get("Quantity", "")
        price = msg.get("Price", "")
        profit = msg.get("Profit", "")
        dt = msg.get("DateTime", "")
        tag = "FILL-HIST" if tname == "HistoricalOrderFillResponse" else "FILL"
        print(f"[{tag}] {side:<1} {sym:12} Qty={qty:>4} Price={price:>10} P/L={profit:>10} Time={dt}")
    elif tname.startswith("MarketDataUpdate"):
        sym = msg.get("Symbol", "")
        price = msg.get("Price", msg.get("LastTradePrice", ""))
        print(f"[MD] {tname:<30} {sym} {price}")
    elif tname in ("MarketDataReject",):
        print(f"[MD REJECT] {msg}")
    elif tname in ("UserMessage", "GeneralLogMessage", "AlertMessage"):
        txt = msg.get("Text", msg)
        print(f"[MSG] {txt}")
    else:
        compact = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        if len(compact) > 240:
            compact = compact[:240] + "Ã¢â‚¬Â¦"
        print(f"[{tname}] {compact}")

    if file_log:
        json.dump(msg, file_log, separators=(",", ":"), ensure_ascii=False)
        file_log.write("\n")
        file_log.flush()


def main():
    parser = argparse.ArgumentParser(description="Probe Sierra Chart DTC JSON server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11099)
    parser.add_argument("--probe", action="store_true", help="Run built-in probe routine")
    parser.add_argument("--username", default="", help="Optional username")
    parser.add_argument("--password", default="", help="Optional password")
    parser.add_argument("--trade-account", default="", help="Optional TradeAccount filter for some requests")
    parser.add_argument("--logfile", default="dtc_probe_output.jsonl", help="Raw JSONL dump file")
    args = parser.parse_args()

    import contextlib

    try:
        file_context = open(args.logfile, "w", encoding="utf-8")  # noqa: SIM115
    except Exception as e:
        print(f"[WARN] Could not open logfile '{args.logfile}': {e}", file=sys.stderr)
        file_context = contextlib.nullcontext(None)

    with file_context as file_log:

        def on_msg(msg):
            pretty_print_msg(msg, file_log)

        print(f"Connecting to DTC server {args.host}:{args.port} ...")
        client = DTCClientJSON(
            args.host,
            args.port,
            on_msg=on_msg,
            trade_account=(args.trade_account or None),
            # UI wires go in the app that imports this module.
            # on_position=..., on_order=..., on_order_fill=..., on_account_balance=..., on_trade_account=...
            # on_md_trade=..., on_md_bidask=..., on_security_definition=...
        )
        try:
            client.connect(username=args.username, password=args.password)
            time.sleep(1.0)
            if args.probe:
                client.probe_server()
            print("Press Ctrl+C to stop listening...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            client.close()


if __name__ == "__main__":
    main()
