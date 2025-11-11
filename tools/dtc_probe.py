#!/usr/bin/env python3
# -------------------- [Unified DTC Probe] (start)

"""
Unified DTC Probe
-----------------
Comprehensive diagnostic tool for Sierra Chart DTC connections.
Merges dtc_health_check.py, dtc_probe.py, and dtc_positions_check.py functionality.

Usage:
    python tools/dtc_probe.py --mode health
    python tools/dtc_probe.py --mode live
    python tools/dtc_probe.py --mode order-test
    python tools/dtc_probe.py --mode positions

Modes:
    health      → runs complete connection + data + heartbeat audit
    live        → connects and streams all messages continuously
    order-test  → submits and cancels a test order in SIM account
    positions   → queries and displays positions for all accounts

Environment Variables:
    DTC_HOST=127.0.0.1
    DTC_PORT=11099
    DTC_ENCODING=json-compact-null
    DTC_TRADE_ACCOUNT=Sim1
    DEBUG_DTC=1
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import queue
import socket
import sys
import threading
import time
import traceback
from typing import Any, Dict, Optional


__scope__ = "dtc.probe"


# ================================================================
#  Console Utilities
# ================================================================


class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str, color: str = Color.RESET) -> None:
    print(f"{color}[{ts()}] {msg}{Color.RESET}")


# ================================================================
#  DTC Client
# ================================================================


class DTCClient:
    def __init__(self, host: str, port: int, encoding: str, trade_account: str):
        self.host = host
        self.port = port
        self.encoding = encoding
        self.trade_account = trade_account
        self.sock: Optional[socket.socket] = None
        self.recv_thread: Optional[threading.Thread] = None
        self.running = False
        self.q = queue.Queue()
        self.results: dict[str, bool] = {}

    # ------------------------------------------------------------
    #  Connection Lifecycle
    # ------------------------------------------------------------

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            log(f"Connected to {self.host}:{self.port}", Color.GREEN)
            self.running = True
            self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self.recv_thread.start()
            return True
        except Exception as e:
            log(f"Connection failed: {e}", Color.RED)
            self.results["connect"] = False
            return False

    def disconnect(self) -> None:
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
        log("Disconnected", Color.YELLOW)

    # ------------------------------------------------------------
    #  Send / Receive
    # ------------------------------------------------------------

    def send(self, msg: dict[str, Any]) -> None:
        if not self.sock:
            return
        try:
            raw = json.dumps(msg).encode("utf-8") + b"\x00"
            self.sock.sendall(raw)
            if os.getenv("DEBUG_DTC"):
                log(f"→ {msg}", Color.CYAN)
        except Exception as e:
            log(f"Send failed: {e}", Color.RED)

    def _recv_loop(self) -> None:
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\x00" in buf:
                    idx = buf.index(b"\x00")
                    chunk = buf[:idx]
                    buf = buf[idx + 1 :]
                    if chunk:
                        try:
                            msg = json.loads(chunk.decode("utf-8"))
                            self.q.put(msg)
                            if os.getenv("DEBUG_DTC"):
                                log(f"← {msg}", Color.BLUE)
                        except json.JSONDecodeError:
                            continue
            except (socket.timeout, OSError):
                continue
            except Exception as e:
                log(f"Recv error: {e}", Color.RED)
                break
        self.running = False

    # ------------------------------------------------------------
    #  Helper utilities
    # ------------------------------------------------------------

    def recv_any(self, timeout: float = 2.0) -> Optional[dict[str, Any]]:
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait_for_type(self, t: int, timeout: float = 5.0) -> Optional[dict[str, Any]]:
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = self.recv_any(0.5)
            if msg and msg.get("Type") == t:
                return msg
        return None

    # ------------------------------------------------------------
    #  Core Protocol Actions
    # ------------------------------------------------------------

    def logon(self) -> bool:
        log("Sending LogonRequest", Color.YELLOW)
        msg = {
            "Type": 1,
            "ProtocolVersion": 8,
            "Username": "",
            "Password": "",
            "ClientName": "UnifiedDTCProbe",
            "HeartbeatIntervalInSeconds": 5,
            "TradeMode": 1,
        }
        self.send(msg)
        resp = self.wait_for_type(2)
        if resp and resp.get("Result") == 1:
            log("LogonResponse OK", Color.GREEN)
            self.results["logon"] = True
            return True
        log("LogonResponse failed or timeout", Color.RED)
        self.results["logon"] = False
        return False

    def request_accounts(self) -> bool:
        self.send({"Type": 600})
        msg = self.wait_for_type(600)
        if msg and "TradeAccount" in msg:
            log(f"TradeAccount={msg['TradeAccount']}", Color.GREEN)
            self.results["accounts"] = True
            return True
        log("No TradeAccounts received", Color.RED)
        self.results["accounts"] = False
        return False

    def request_balance(self) -> bool:
        self.send({"Type": 400})
        msg = self.wait_for_type(400)
        if msg and any(k in msg for k in ("Balance", "CashBalance")):
            log("Balance info received", Color.GREEN)
            self.results["balance"] = True
            return True
        log("No balance info", Color.RED)
        self.results["balance"] = False
        return False

    def request_positions(self) -> bool:
        self.send({"Type": 500})
        msg = self.wait_for_type(500)
        if msg and "Symbol" in msg:
            log(f"Position symbol={msg['Symbol']}", Color.GREEN)
            self.results["positions"] = True
            return True
        log("No positions returned", Color.YELLOW)
        self.results["positions"] = False
        return False

    def request_positions_detailed(self) -> list:
        """
        Request and return detailed position information for all accounts.
        Merged from dtc_positions_check.py functionality.

        Returns:
            List of position dictionaries
        """
        positions = []

        # Get trade accounts first
        self.send({"Type": 400, "RequestID": 1})
        accounts = []

        # Collect trade account responses
        t0 = time.time()
        while time.time() - t0 < 2:
            msg = self.recv_any(0.5)
            if msg:
                if msg.get("Type") == 401:  # TRADE_ACCOUNT_RESPONSE
                    account = msg.get("TradeAccount")
                    if account:
                        accounts.append(account)
                        log(f"Found account: {account}", Color.GREEN)

        if not accounts:
            log("No accounts found", Color.RED)
            return positions

        # Query positions for each account
        for account in accounts:
            log(f"Requesting positions for {account}...", Color.YELLOW)
            self.send(
                {
                    "Type": 500,  # CURRENT_POSITIONS_REQUEST
                    "RequestID": 2,
                    "TradeAccount": account,
                }
            )

            # Collect position responses
            t0 = time.time()
            while time.time() - t0 < 2:
                msg = self.recv_any(0.5)
                if msg:
                    if msg.get("Type") == 306:  # POSITION_UPDATE
                        symbol = msg.get("Symbol")
                        qty = msg.get("Quantity") or msg.get("PositionQuantity") or 0
                        avg_price = msg.get("AveragePrice") or msg.get("avg_entry")

                        position_info = {
                            "account": account,
                            "symbol": symbol,
                            "quantity": qty,
                            "average_price": avg_price,
                        }
                        positions.append(position_info)

                        if qty != 0:
                            log(f"  OPEN: {symbol:20} | Qty: {qty:6} | AvgPrice: {avg_price}", Color.GREEN)
                        else:
                            log(f"  CLOSED: {symbol:20} | Qty: {qty:6}", Color.CYAN)

        return positions

    def subscribe_market_data(self, symbol: str) -> bool:
        self.send({"Type": 101, "Symbol": symbol})
        msg = self.wait_for_type(103)
        if msg and "Price" in msg:
            log(f"Market data for {symbol} OK", Color.GREEN)
            self.results["market_data"] = True
            return True
        log(f"No market data for {symbol}", Color.RED)
        self.results["market_data"] = False
        return False

    def submit_test_order(self, symbol: str) -> bool:
        acct = self.trade_account or "Sim1"
        self.send(
            {
                "Type": 300,
                "TradeAccount": acct,
                "ClientOrderID": "TESTORDER",
                "Symbol": symbol,
                "BuySell": 1,
                "OrderType": 1,
                "Price1": 5000,
                "OrderQuantity": 1,
            }
        )
        msg = self.wait_for_type(301, 3.0)
        if msg and msg.get("OrderStatus") in ("Open", "Working"):
            log("Test order accepted", Color.GREEN)
            self.results["order"] = True
            return True
        log("Test order rejected or no response", Color.RED)
        self.results["order"] = False
        return False

    def cancel_test_order(self, symbol: str) -> None:
        acct = self.trade_account or "Sim1"
        self.send({"Type": 302, "TradeAccount": acct, "Symbol": symbol})
        log("Cancel request sent", Color.YELLOW)

    # ------------------------------------------------------------
    #  Health Audit Summary
    # ------------------------------------------------------------

    def summary(self) -> None:
        print(f"\n{Color.BLUE}{'='*80}")
        print("DTC HEALTH SUMMARY")
        print(f"{'='*80}{Color.RESET}")
        for key, ok in self.results.items():
            color = Color.GREEN if ok else Color.RED
            print(f"{color}{key:<15}: {'PASS' if ok else 'FAIL'}{Color.RESET}")
        print()


# ================================================================
#  Probe Modes
# ================================================================


def run_health(client: DTCClient) -> None:
    if not client.connect():
        return
    try:
        client.logon()
        client.request_accounts()
        client.request_balance()
        client.request_positions()
        client.subscribe_market_data("MESZ25")
        client.summary()
    finally:
        client.disconnect()


def run_live(client: DTCClient) -> None:
    if not client.connect():
        return
    try:
        client.logon()
        log("Entering continuous receive mode...", Color.YELLOW)
        while True:
            msg = client.recv_any(5.0)
            if msg:
                t = msg.get("Type")
                log(f"Type={t} → {msg}", Color.CYAN)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


def run_order_test(client: DTCClient) -> None:
    if not client.connect():
        return
    try:
        client.logon()
        client.submit_test_order("MESZ25")
        time.sleep(1)
        client.cancel_test_order("MESZ25")
        client.summary()
    finally:
        client.disconnect()


def run_positions(client: DTCClient) -> None:
    """
    Query and display detailed positions for all accounts.
    Merged from dtc_positions_check.py functionality.
    """
    if not client.connect():
        return
    try:
        client.logon()
        log("Querying positions for all accounts...", Color.YELLOW)
        positions = client.request_positions_detailed()

        log(f"\nFound {len(positions)} total position records", Color.BLUE)
        open_positions = [p for p in positions if p.get("quantity", 0) != 0]
        if open_positions:
            log(f"{len(open_positions)} open positions", Color.GREEN)
        else:
            log("No open positions", Color.CYAN)
    finally:
        client.disconnect()


# ================================================================
#  Main
# ================================================================


def main(argv: list[str] = None) -> int:
    """
    Main entry point for DTC probe.

    Args:
        argv: Command line arguments (or None to use sys.argv)

    Returns:
        0 on success, non-zero on failure
    """
    parser = argparse.ArgumentParser(description="Unified DTC Probe")
    parser.add_argument(
        "--mode",
        choices=["health", "live", "order-test", "positions"],
        default="health",
        help="Probe mode: health check, live stream, order test, or positions query",
    )
    args = parser.parse_args(argv)

    host = os.getenv("DTC_HOST", "127.0.0.1")
    port = int(os.getenv("DTC_PORT", "11099"))
    encoding = os.getenv("DTC_ENCODING", "json-compact-null")
    trade_account = os.getenv("DTC_TRADE_ACCOUNT", "Sim1")

    log(f"Host={host} Port={port} Encoding={encoding} Account={trade_account}", Color.BLUE)
    log(f"Mode={args.mode}", Color.BLUE)

    client = DTCClient(host, port, encoding, trade_account)

    try:
        if args.mode == "health":
            run_health(client)
        elif args.mode == "live":
            run_live(client)
        elif args.mode == "order-test":
            run_order_test(client)
        elif args.mode == "positions":
            run_positions(client)
        else:
            log("Unknown mode", Color.RED)
            return 1
        return 0
    except Exception as e:
        log(f"Probe failed: {e}", Color.RED)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# -------------------- [Unified DTC Probe] (end)
