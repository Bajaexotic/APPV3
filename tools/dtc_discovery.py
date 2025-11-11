#!/usr/bin/env python3
# -------------------- [DTC Discovery Tool] (start)

"""
DTC MESSAGE DISCOVERY TOOL  —  Unified Version
----------------------------------------------
Combines 'discover_all_dtc_messages.py' (baseline) and
'discover_extended_dtc_messages.py' (aggressive discovery)
into a single safe, mode-selectable utility.

Usage
-----
    python tools/dtc/dtc_discovery.py --mode base
    python tools/dtc/dtc_discovery.py --mode extended

Modes
-----
--mode base
    Runs safe baseline discovery: connects, logs on, requests
    accounts, positions, orders, balances, and maps all message
    types and fields observed.

--mode extended
    Adds exploratory requests covering market depth, statistics,
    security definitions, and simulated order flows.
    ⚠️  Use only on SIM accounts.

Outputs
-------
Console log + optional JSON summary (--out <file>).
"""

import argparse
from collections import defaultdict
from datetime import datetime
import json
import os
import socket
import time
from typing import Any, Dict, List, Set

import psutil


__scope__ = "dtc.discovery"


# ================================================================
#  Utility Helpers
# ================================================================


def timestamp() -> str:
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def safe_send(sock: socket.socket, msg: dict[str, Any]) -> bool:
    """Send a null-terminated JSON DTC message."""
    try:
        sock.sendall(json.dumps(msg).encode("utf-8") + b"\x00")
        return True
    except Exception as e:
        print(f"[{timestamp()}] [FAIL] send error: {e}")
        return False


def safe_recv(sock: socket.socket, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Receive and decode all JSON messages within timeout."""
    sock.settimeout(timeout)
    buffer = b""
    messages: list[dict[str, Any]] = []
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\x00" in buffer:
                idx = buffer.index(b"\x00")
                raw = buffer[:idx]
                buffer = buffer[idx + 1 :]
                if raw:
                    try:
                        msg = json.loads(raw.decode("utf-8"))
                        messages.append(msg)
                    except json.JSONDecodeError:
                        pass
    except socket.timeout:
        pass
    except Exception:
        pass
    return messages


# ================================================================
#  DTC Discovery Class
# ================================================================


class DTCDiscovery:
    """Unified discovery engine supporting base and extended modes."""

    def __init__(self, host: str = "127.0.0.1", port: int = 11099):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.messages: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self.all_types: set[int] = set()
        self.all_fields: dict[int, set[str]] = defaultdict(set)
        self.req_id = 100
        self.accounts: list[str] = []

    # ------------------------------------------------------------
    #  Connection / Setup
    # ------------------------------------------------------------

    def connect(self) -> bool:
        print(f"[{timestamp()}] Connecting to {self.host}:{self.port}")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"[{timestamp()}] [OK] Connected")
            return True
        except Exception as e:
            print(f"[{timestamp()}] [FAIL] {e}")
            return False

    def disconnect(self) -> None:
        if self.sock:
            self.sock.close()
            print(f"[{timestamp()}] Connection closed")

    def next_req(self) -> int:
        self.req_id += 1
        return self.req_id

    # ------------------------------------------------------------
    #  Core Logic
    # ------------------------------------------------------------

    def _record(self, msgs: list[dict[str, Any]]) -> None:
        for msg in msgs:
            t = msg.get("Type")
            if not t:
                continue
            self.messages[t].append(msg)
            self.all_types.add(t)
            for f in msg:
                self.all_fields[t].add(f)

    # ------------------------------------------------------------
    #  Discovery Steps
    # ------------------------------------------------------------

    def logon(self) -> None:
        print(f"\n{'='*80}\n[STEP 0] LOGON\n{'='*80}")
        msg = {
            "Type": 1,
            "ProtocolVersion": 8,
            "ClientName": "UnifiedDiscovery",
            "HeartbeatIntervalInSeconds": 5,
            "Username": "",
            "Password": "",
            "TradeMode": 1,
            "OrderUpdatesAsConnectionDefault": 1,
        }
        safe_send(self.sock, msg)
        self._record(safe_recv(self.sock, 2))

    def get_accounts(self) -> None:
        print(f"\n{'='*80}\n[STEP 1] GET TRADE ACCOUNTS (Type 400)\n{'='*80}")
        safe_send(self.sock, {"Type": 400, "RequestID": self.next_req()})
        msgs = safe_recv(self.sock, 2)
        self._record(msgs)
        self.accounts = [m.get("TradeAccount") for m in msgs if m.get("TradeAccount")]
        print(f"  Accounts: {self.accounts}")

    def request_positions(self) -> None:
        print(f"\n{'='*80}\n[STEP 2] REQUEST POSITIONS (Type 500)\n{'='*80}")
        safe_send(self.sock, {"Type": 500, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def request_open_orders(self) -> None:
        print(f"\n{'='*80}\n[STEP 3] OPEN ORDERS (Type 305)\n{'='*80}")
        safe_send(self.sock, {"Type": 305, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def request_balance(self) -> None:
        print(f"\n{'='*80}\n[STEP 4] ACCOUNT BALANCE (Type 601)\n{'='*80}")
        safe_send(self.sock, {"Type": 601, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    # --------------------- EXTENDED REQUESTS --------------------

    def request_market_depth(self) -> None:
        print(f"\n{'='*80}\n[EXT] MARKET DEPTH (Type 101)\n{'='*80}")
        safe_send(self.sock, {"Type": 101, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def request_market_data(self) -> None:
        print(f"\n{'='*80}\n[EXT] MARKET DATA (Type 102)\n{'='*80}")
        safe_send(self.sock, {"Type": 102, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def request_security_def(self) -> None:
        print(f"\n{'='*80}\n[EXT] SECURITY DEFINITION (Type 15)\n{'='*80}")
        safe_send(self.sock, {"Type": 15, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def request_current_price(self) -> None:
        print(f"\n{'='*80}\n[EXT] CURRENT PRICE (Type 34)\n{'='*80}")
        safe_send(self.sock, {"Type": 34, "RequestID": self.next_req()})
        self._record(safe_recv(self.sock, 2))

    def submit_test_order(self) -> None:
        if not self.accounts:
            print("  No accounts available, skipping order test.")
            return
        print(f"\n{'='*80}\n[EXT] SUBMIT TEST ORDER (Type 300)\n{'='*80}")
        msg = {
            "Type": 300,
            "RequestID": self.next_req(),
            "TradeAccount": self.accounts[0],
            "ClientOrderID": "DISCOVERY_TEST",
            "Symbol": "MESZ25",
            "Exchange": "CME",
            "BuySell": 1,
            "OrderType": 1,
            "OrderQuantity": 1,
            "Price1": 6000,
        }
        safe_send(self.sock, msg)
        self._record(safe_recv(self.sock, 2))

    def cancel_test_order(self) -> None:
        print(f"\n{'='*80}\n[EXT] CANCEL ORDER (Type 302)\n{'='*80}")
        msg = {
            "Type": 302,
            "RequestID": self.next_req(),
            "ServerOrderID": "NONEXISTENT",
            "TradeAccount": self.accounts[0] if self.accounts else "",
        }
        safe_send(self.sock, msg)
        self._record(safe_recv(self.sock, 2))

    # ------------------------------------------------------------
    #  Reporting
    # ------------------------------------------------------------

    def summary(self, out_file: str | None = None) -> None:
        print(f"\n{'='*100}\nDISCOVERY SUMMARY\n{'='*100}")
        print(f"Unique message types: {len(self.all_types)}\n")
        for t in sorted(self.all_types):
            count = len(self.messages[t])
            fields = sorted(list(self.all_fields[t]))
            print(f"Type {t}: {count} messages, {len(fields)} fields")
            print(f"  Fields: {', '.join(fields[:10])}")
        if out_file:
            summary = {
                "timestamp": timestamp(),
                "types": sorted(list(self.all_types)),
                "field_map": {str(k): sorted(list(v)) for k, v in self.all_fields.items()},
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"\nSummary written to {out_file}")

    # ------------------------------------------------------------
    #  Runner
    # ------------------------------------------------------------

    def run(self, mode: str = "base", out_file: str | None = None) -> None:
        if not self.connect():
            return
        self.logon()
        self.get_accounts()
        self.request_positions()
        self.request_open_orders()
        self.request_balance()

        if mode == "extended":
            self.request_market_depth()
            self.request_market_data()
            self.request_security_def()
            self.request_current_price()
            self.submit_test_order()
            self.cancel_test_order()
            print(f"\n{'='*80}\n[EXT] WAITING FOR UNSOLICITED (5s)\n{'='*80}")
            self._record(safe_recv(self.sock, 5))

        self.disconnect()
        self.summary(out_file)


# ================================================================
#  Main Entrypoint
# ================================================================


def ensure_single_instance(tag: str = "dtc_discovery") -> None:
    """Abort if another discovery process with same tag is running."""
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or [])
            if tag in cmd and proc.pid != os.getpid():
                print(f"[{timestamp()}] Another '{tag}' process (PID {proc.pid}) is active. Exiting.")
                raise SystemExit(1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified DTC Message Discovery Tool")
    parser.add_argument("--host", default="127.0.0.1", help="DTC server host")
    parser.add_argument("--port", type=int, default=11099, help="DTC server port")
    parser.add_argument("--mode", choices=["base", "extended"], default="base", help="Discovery mode")
    parser.add_argument("--out", help="Optional JSON summary output path")
    args = parser.parse_args()

    ensure_single_instance("dtc_discovery")

    print("\n" + "=" * 100)
    print(f"DTC MESSAGE DISCOVERY (mode={args.mode})")
    print("=" * 100 + "\n")

    tool = DTCDiscovery(host=args.host, port=args.port)
    tool.run(mode=args.mode, out_file=args.out)


if __name__ == "__main__":
    main()

# -------------------- [DTC Discovery Tool] (end)
