#!/usr/bin/env python3
"""
Debug script to capture and display ALL DTC messages from Sierra Chart.
Run this while connected to your DTC server to see exactly what's being sent.
"""

import json
from pathlib import Path
import socket
import sys


# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

import builtins
import contextlib

from utils.logger import get_logger


log = get_logger(__name__)


def connect_and_capture(host="127.0.0.1", port=11099, duration_sec=30):
    """Connect to DTC and capture all messages for specified duration."""
    print(f"\n{'='*80}")
    print("DTC MESSAGE CAPTURE")
    print(f"{'='*80}")
    print(f"Connecting to {host}:{port}")
    print(f"Capturing for {duration_sec} seconds...")
    print(f"{'='*80}\n")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"✓ Connected to {host}:{port}\n")

        # Set timeout
        sock.settimeout(duration_sec)

        # Send logon request
        logon = {"Type": 1, "ProtocolVersion": 12, "Username": "admin", "Password": "admin"}
        sock.send((json.dumps(logon) + "\x00").encode())
        print(f"→ Sent LOGON: {logon}\n")

        # Capture messages
        buffer = b""
        message_count = 0
        message_types = {}

        print(f"{'TIME':<12} {'TYPE':<6} {'NAME':<30} {'CONTENT PREVIEW':<40}")
        print(f"{'-'*12} {'-'*6} {'-'*30} {'-'*40}")

        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    print("\n✗ Connection closed by server")
                    break

                buffer += chunk

                # Process complete messages (null-terminated JSON)
                while b"\x00" in buffer:
                    msg_bytes, buffer = buffer.split(b"\x00", 1)

                    try:
                        msg = json.loads(msg_bytes.decode("utf-8"))
                        message_count += 1
                        msg_type = msg.get("Type", "?")

                        # Track message types
                        if msg_type not in message_types:
                            message_types[msg_type] = 0
                        message_types[msg_type] += 1

                        # Format type name
                        type_names = {
                            1: "LOGON_REQ",
                            2: "LOGON_RSP",
                            3: "HEARTBEAT",
                            300: "SUBMIT_ORDER",
                            301: "ORDER_UPD",
                            306: "POSITION",
                            400: "ACCTS_REQ",
                            401: "ACCT_RSP",
                            500: "POS_REQ",
                            501: "MKT_DATA",
                            502: "POS_RSP",
                            600: "BALANCE_UPD",
                            601: "BALANCE_REQ",
                            602: "BALANCE_RSP",
                        }
                        type_name = type_names.get(msg_type, f"Type{msg_type}")

                        # Format preview
                        if "Type" in msg:
                            preview = f"Type={msg_type}"
                            if "Symbol" in msg:
                                preview += f" Symbol={msg['Symbol']}"
                            if "balance" in msg:
                                preview += f" balance={msg['balance']}"
                            if "Quantity" in msg:
                                preview += f" qty={msg['Quantity']}"
                            if "AccountValue" in msg:
                                preview += f" acct={msg['AccountValue']}"
                        else:
                            preview = f"(NO TYPE FIELD!) Keys: {list(msg.keys())[:3]}"

                        print(f"{message_count:<12} {msg_type!s:<6} {type_name:<30} {preview:<40}")

                    except json.JSONDecodeError:
                        print(f"  ERROR: Could not parse JSON: {msg_bytes[:50]}")

        except socket.timeout:
            print(f"\n✓ Timeout reached ({duration_sec}s)")

        print(f"\n{'='*80}")
        print("CAPTURE COMPLETE")
        print(f"{'='*80}")
        print(f"Total messages: {message_count}")
        print("\nMessage type distribution:")
        for msg_type in sorted(message_types.keys(), key=lambda x: message_types[x], reverse=True):
            count = message_types[msg_type]
            type_names = {
                1: "LOGON_REQ",
                2: "LOGON_RSP",
                3: "HEARTBEAT",
                300: "SUBMIT_ORDER",
                301: "ORDER_UPD",
                306: "POSITION",
                400: "ACCTS_REQ",
                401: "ACCT_RSP",
                500: "POS_REQ",
                501: "MKT_DATA",
                502: "POS_RSP",
                600: "BALANCE_UPD",
                601: "BALANCE_REQ",
                602: "BALANCE_RSP",
            }
            type_name = type_names.get(msg_type, f"Type{msg_type}")
            print(f"  Type {msg_type:<4} ({type_name:<15}): {count:>4} messages")

        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        with contextlib.suppress(builtins.BaseException):
            sock.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Capture DTC messages")
    parser.add_argument("--host", default="127.0.0.1", help="DTC server host")
    parser.add_argument("--port", type=int, default=11099, help="DTC server port")
    parser.add_argument("--duration", type=int, default=30, help="Capture duration in seconds")
    args = parser.parse_args()

    connect_and_capture(args.host, args.port, args.duration)
