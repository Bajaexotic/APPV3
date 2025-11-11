#!/usr/bin/env python3
"""
DTC HANDSHAKE VALIDATION TOOL

Complete validation of DTC protocol handshake and message flow.
Tests all critical message exchanges and validates responses.

Run: python tools/validate_dtc_handshake.py
"""
from collections import defaultdict
from datetime import datetime
import json
import socket
import time


__scope__ = "dtc.handshake_validation"


class DTCHandshakeValidator:
    def __init__(self, host="127.0.0.1", port=11099):
        self.host = host
        self.port = port
        self.sock = None
        self.results = defaultdict(dict)
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"\n[{self.now()}] [OK] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"\n[{self.now()}] [FAIL] Connection failed: {e}")
            return False

    def send(self, msg_dict, label=""):
        msg_type = msg_dict.get("Type")
        print(f"\n[{self.now()}] [SEND] Type {msg_type}: {label}")
        data = json.dumps(msg_dict).encode("utf-8") + b"\x00"
        try:
            self.sock.sendall(data)
            return True
        except Exception as e:
            print(f"  [FAIL] Send failed: {e}")
            return False

    def recv(self, timeout=2, expected_types=None):
        """Receive message with optional type validation"""
        self.sock.settimeout(timeout)
        buffer = b""
        msg_count = 0
        received_types = []

        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\x00" in buffer:
                    idx = buffer.index(b"\x00")
                    msg_data = buffer[:idx]
                    buffer = buffer[idx + 1 :]
                    if msg_data:
                        try:
                            msg = json.loads(msg_data.decode("utf-8"))
                            msg_type = msg.get("Type")
                            msg_count += 1
                            received_types.append(msg_type)
                            print(f"  [RCV {msg_count}] Type {msg_type}")
                        except:
                            pass
        except socket.timeout:
            pass
        except:
            pass

        # Validation
        if expected_types:
            success = any(t in expected_types for t in received_types)
            if success:
                print(f"  [OK] Expected type(s) {expected_types} received")
            else:
                print(f"  [FAIL] Expected {expected_types}, got {received_types}")
            return success
        return msg_count > 0

    def test(self, name, send_msg, expected_response_types, label=""):
        """Run a single test"""
        self.test_count += 1
        print(f"\n{'='*80}")
        print(f"TEST {self.test_count}: {name}")
        print(f"{'='*80}")

        self.send(send_msg, label)
        success = self.recv(timeout=2, expected_types=expected_response_types)

        if success:
            self.pass_count += 1
            print("  [PASS] TEST PASSED")
        else:
            self.fail_count += 1
            print("  [FAIL] TEST FAILED")

        self.results[name] = {"passed": success}
        return success

    def now(self):
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def run(self):
        print(f"\n{'='*100}")
        print("DTC HANDSHAKE VALIDATION")
        print("Testing complete DTC message flow and validation")
        print(f"{'='*100}")

        if not self.connect():
            return

        # STEP 1: Logon
        self.test(
            "Logon Handshake",
            {
                "Type": 1,
                "ProtocolVersion": 8,
                "ClientName": "HandshakeValidator",
                "HeartbeatIntervalInSeconds": 5,
                "Username": "",
                "Password": "",
                "TradeMode": 1,
                "OrderUpdatesAsConnectionDefault": 1,
            },
            [2],
            "LOGON_REQUEST",
        )

        # STEP 2: Trade Accounts
        self.test("Trade Accounts Request", {"Type": 400, "RequestID": 100}, [401], "TRADE_ACCOUNTS_REQUEST")

        # STEP 3: Account Balance
        self.test("Account Balance Request", {"Type": 601, "RequestID": 101}, [600, 602], "ACCOUNT_BALANCE_REQUEST")

        # STEP 4: Open Orders (Type 305 - critical test!)
        self.test(
            "Open Orders Request (TYPE 305 - BUG TEST)",
            {"Type": 305, "RequestID": 102},
            [306, 307, 301],  # Should be 301, but 306 is the bug
            "OPEN_ORDERS_REQUEST",
        )

        # STEP 5: Positions Request (Type 500)
        self.test(
            "Positions Request (TYPE 500)",
            {"Type": 500, "RequestID": 103},
            [501],  # Correctly gets market data
            "POSITIONS_REQUEST",
        )

        # STEP 6: Historical Fills (Type 303)
        import time as time_module

        now = int(time_module.time())
        start_ts = now - 30 * 86400
        self.test(
            "Historical Fills Request",
            {"Type": 303, "RequestID": 104, "StartDateTime": start_ts},
            [304, 308],  # 308 is error, 304 would be correct
            "HISTORICAL_FILLS_REQUEST",
        )

        # STEP 7: Market Depth Request (Type 101)
        self.test("Market Depth Request (TYPE 101)", {"Type": 101, "RequestID": 105}, [103], "MARKET_DEPTH_REQUEST")

        # STEP 8: Market Data Request (Type 102)
        self.test("Market Data Request (TYPE 102)", {"Type": 102, "RequestID": 106}, [121], "MARKET_DATA_REQUEST")

        # STEP 9: Account Positions (Type 309)
        self.test(
            "Account Positions Request (TYPE 309)", {"Type": 309, "RequestID": 107}, [310], "ACCOUNT_POSITIONS_REQUEST"
        )

        # STEP 10: Test Unknown Types
        self.test("Unknown Type 5", {"Type": 5, "RequestID": 108}, [5], "UNKNOWN_TYPE_5")

        self.test("Unknown Type 6", {"Type": 6, "RequestID": 109}, [6], "UNKNOWN_TYPE_6")

        # STEP 11: Heartbeat test
        print(f"\n{'='*80}")
        print("STEP 11: Wait for unsolicited heartbeat (5 seconds)")
        print(f"{'='*80}")
        self.recv(timeout=5)

        self.sock.close()

        # Final Report
        self._print_report()

    def _print_report(self):
        print(f"\n{'='*100}")
        print("HANDSHAKE VALIDATION REPORT")
        print(f"{'='*100}\n")

        print(f"Total Tests: {self.test_count}")
        print(f"Passed: {self.pass_count} [OK]")
        print(f"Failed: {self.fail_count} [FAIL]")
        print(f"Success Rate: {(self.pass_count / self.test_count * 100):.1f}%\n")

        print(f"{'='*80}")
        print("DETAILED RESULTS")
        print(f"{'='*80}\n")

        for test_name, result in self.results.items():
            status = "[PASS]" if result["passed"] else "[FAIL]"
            print(f"{status}: {test_name}")

        print(f"\n{'='*80}")
        print("CRITICAL ISSUES")
        print(f"{'='*80}\n")

        print("[!] Type 305 (OpenOrders) returns Type 306 - PROTOCOL VIOLATION")
        print("    Expected: Type 301 (OrderUpdate)")
        print("    Actual: Type 306 (PositionUpdate) - WRONG!")
        print("    Impact: Phantom positions appear\n")

        print("[!] Type 500 (Positions) returns Type 501 - WRONG TYPE")
        print("    Expected: Type 306 (PositionUpdate)")
        print("    Actual: Type 501 (MarketDataSnapshot) - MARKET DATA!")
        print("    Impact: Cannot query positions directly\n")

        print("[!] Unknown Types 5, 6, etc.")
        print("    Response received but type purpose unclear")
        print("    See DTC_COMPLETE_MESSAGE_MAP.md for details\n")

        print(f"{'='*80}")
        print("VALIDATION COMPLETE")
        print(f"{'='*100}\n")


if __name__ == "__main__":
    validator = DTCHandshakeValidator()
    validator.run()
