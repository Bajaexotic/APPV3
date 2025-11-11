#!/usr/bin/env python3
"""
DTC Handshake Capture Tool
Connects to Sierra Chart DTC and captures the complete handshake + first N messages.
Shows EXACTLY what Sierra Chart is sending without any assumptions.
"""

import builtins
import contextlib
from datetime import datetime
import json
from pathlib import Path
import socket
import sys


sys.path.insert(0, str(Path(__file__).parent))


def format_message(msg_dict, max_width=120):
    """Pretty print a DTC message"""
    msg_type = msg_dict.get("Type", "?")
    msg_json = json.dumps(msg_dict, indent=2)
    lines = msg_json.split("\n")

    # Color code by message type
    if msg_type == 1:
        prefix = "→ [SEND] LOGON_REQUEST"
    elif msg_type == 2:
        prefix = "← [RECV] LOGON_RESPONSE"
    elif msg_type == 3:
        prefix = "← [RECV] HEARTBEAT"
    elif msg_type == 400:
        prefix = "→ [SEND] TRADE_ACCOUNTS_REQUEST"
    elif msg_type == 401:
        prefix = "← [RECV] TRADE_ACCOUNT_RESPONSE"
    elif msg_type == 500:
        prefix = "→ [SEND] POSITIONS_REQUEST"
    elif msg_type == 306:
        prefix = "← [RECV] POSITION_UPDATE"
    elif msg_type == 601:
        prefix = "→ [SEND] BALANCE_REQUEST"
    elif msg_type in (600, 602):
        prefix = f"← [RECV] BALANCE_UPDATE (Type {msg_type})"
    else:
        prefix = f"← [RECV] Type {msg_type}"

    print(f"\n{prefix}")
    print("─" * max_width)
    for line in lines:
        print(line)
    print("─" * max_width)


def capture_handshake(host="127.0.0.1", port=11099, timeout=10, max_messages=20):
    """
    Connect to DTC and capture the complete handshake.
    Shows exactly what Sierra Chart sends.
    """
    print("\n" + "=" * 80)
    print("DTC HANDSHAKE CAPTURE")
    print("=" * 80)
    print(f"Target: {host}:{port}")
    print(f"Timeout: {timeout}s")
    print(f"Max messages to capture: {max_messages}")
    print("=" * 80)

    sock = None
    try:
        # Connect
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected\n")

        # Send logon
        logon_msg = {"Type": 1, "ProtocolVersion": 12, "Username": "admin", "Password": "admin"}
        format_message(logon_msg)
        sock.send((json.dumps(logon_msg) + "\x00").encode())

        # Capture responses
        buffer = b""
        message_count = 0
        messages = []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for responses...\n")

        try:
            while message_count < max_messages:
                chunk = sock.recv(4096)
                if not chunk:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Connection closed by server")
                    break

                buffer += chunk

                # Process all complete messages in buffer
                while b"\x00" in buffer:
                    msg_bytes, buffer = buffer.split(b"\x00", 1)

                    try:
                        msg = json.loads(msg_bytes.decode("utf-8"))
                        message_count += 1
                        messages.append(msg)
                        format_message(msg)

                    except json.JSONDecodeError as e:
                        print(f"\n✗ JSON DECODE ERROR: {e}")
                        print(f"Raw bytes: {msg_bytes[:100]}")

                # Check for timeout
                if message_count > 0:
                    break

        except socket.timeout:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Timeout waiting for messages")

        # Summary
        print(f"\n{'='*80}")
        print("CAPTURE COMPLETE")
        print(f"{'='*80}")
        print(f"Messages received: {message_count}")

        if messages:
            print("\nMessage type summary:")
            type_map = {
                1: "LOGON_REQUEST",
                2: "LOGON_RESPONSE",
                3: "HEARTBEAT",
                400: "TRADE_ACCOUNTS_REQUEST",
                401: "TRADE_ACCOUNT_RESPONSE",
                500: "POSITIONS_REQUEST",
                306: "POSITION_UPDATE",
                600: "ACCOUNT_BALANCE_UPDATE",
                601: "ACCOUNT_BALANCE_REQUEST",
                602: "ACCOUNT_BALANCE_RESPONSE",
            }

            for msg in messages:
                msg_type = msg.get("Type", "?")
                type_name = type_map.get(msg_type, f"Type {msg_type}")
                print(f"  - {type_name}")

                # Show key fields
                if msg_type == 2:
                    print(f"    - LogonStatus: {msg.get('LogonStatus')}")
                    print(f"    - ServerName: {msg.get('ServerName')}")
                elif msg_type == 401:
                    print(f"    - TradeAccount: {msg.get('TradeAccount')}")
                elif msg_type == 306:
                    print(f"    - Symbol: {msg.get('Symbol')}")
                    print(f"    - Quantity: {msg.get('Quantity')}")
                elif msg_type in (600, 602):
                    print(f"    - Has 'balance' field: {'balance' in msg}")
                    print(f"    - Has 'AccountValue' field: {'AccountValue' in msg}")
                    print(f"    - Available fields: {list(msg.keys())}")

        print(f"{'='*80}\n")

        return messages

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return []
    finally:
        if sock:
            with contextlib.suppress(builtins.BaseException):
                sock.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Capture DTC handshake")
    parser.add_argument("--host", default="127.0.0.1", help="DTC host")
    parser.add_argument("--port", type=int, default=11099, help="DTC port")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")
    parser.add_argument("--max-messages", type=int, default=20, help="Max messages to capture")

    args = parser.parse_args()

    messages = capture_handshake(host=args.host, port=args.port, timeout=args.timeout, max_messages=args.max_messages)

    if messages:
        print("\n✓ Successfully captured messages. Review above for details.")
    else:
        print("\n✗ No messages captured. Check your Sierra Chart DTC connection.")
