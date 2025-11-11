#!/usr/bin/env python3
"""
Diagnose Sierra Chart DTC server configuration.
Tests both Binary and JSON encoding capabilities.
"""

import builtins
import contextlib
import json
import socket
import struct
import sys
import time


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

HOST = "127.0.0.1"
PORT = 11099


def test_json_encoding():
    """Test if Sierra accepts JSON encoding negotiation."""
    print("\n" + "=" * 80)
    print("TEST 1: JSON ENCODING NEGOTIATION")
    print("=" * 80)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, PORT))
        print(f"✓ Connected to {HOST}:{PORT}")

        # Send ENCODING_REQUEST for JSON_COMPACT
        encoding_req = {"Type": 5, "ProtocolVersion": 8, "Encoding": 2, "ProtocolType": "DTC"}
        msg = json.dumps(encoding_req).encode("utf-8") + b"\x00"
        sock.send(msg)
        print(f"→ Sent ENCODING_REQUEST: {encoding_req}")

        # Wait for response
        buffer = b""
        start = time.time()

        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    print("✗ Server closed connection (REJECTED)")
                    return False
                buffer += chunk

                while b"\x00" in buffer:
                    idx = buffer.index(b"\x00")
                    frame = buffer[:idx]
                    buffer = buffer[idx + 1 :]

                    if frame:
                        try:
                            msg = json.loads(frame)
                            msg_type = msg.get("Type")

                            if msg_type == 6:  # ENCODING_RESPONSE
                                print(f"✓ ENCODING_RESPONSE received: {msg}")
                                return True
                            elif msg_type == 5:  # LOGOFF
                                print(f"✗ Server sent LOGOFF: {msg.get('Reason', 'Unknown')}")
                                print("\n[DIAGNOSIS] Sierra Chart is rejecting JSON encoding!")
                                print("   Possible causes:")
                                print("   1. DTC server is in Binary-only mode")
                                print("   2. JSON support not enabled in Sierra settings")
                                return False
                            else:
                                print(f"  Received Type {msg_type}: {msg}")
                        except json.JSONDecodeError:
                            print("✗ Invalid JSON (server might be in Binary mode)")
                            print(f"   Raw: {frame[:80]}")
                            return False
            except socket.timeout:
                break

        print("✗ Timeout waiting for ENCODING_RESPONSE")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        with contextlib.suppress(builtins.BaseException):
            sock.close()


def test_binary_encoding():
    """Test if Sierra accepts Binary DTC protocol."""
    print("\n" + "=" * 80)
    print("TEST 2: BINARY DTC PROTOCOL")
    print("=" * 80)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, PORT))
        print(f"✓ Connected to {HOST}:{PORT}")

        # Build Binary LOGON_REQUEST (Type=1)
        # DTC Binary format: [uint16 size][uint16 type][...fields...]
        # For simplicity, send minimal binary header

        # Type 1 = LOGON_REQUEST
        msg_type = 1
        # Minimal size (we'll calculate)

        # Binary fields (little-endian):
        # - Size (uint16)
        # - Type (uint16)
        # - ProtocolVersion (int32)
        # - Username (char[36])
        # - Password (char[36])
        # etc.

        # For diagnosis, just send the header and see if server responds differently
        size = 4  # Just size + type
        data = struct.pack("<HH", size, msg_type)

        sock.send(data)
        print(f"→ Sent Binary LOGON_REQUEST header (Type={msg_type})")

        # Wait for response
        buffer = b""
        start = time.time()

        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    print("✗ Server closed connection")
                    return False
                buffer += chunk

                # Try to decode binary response
                if len(buffer) >= 4:
                    size, msg_type = struct.unpack("<HH", buffer[:4])
                    print(f"✓ Received Binary message: Size={size}, Type={msg_type}")

                    if msg_type == 2:  # LOGON_RESPONSE
                        print("✓ Server accepts BINARY protocol!")
                        return True
                    elif 1 <= msg_type <= 900:
                        print(f"✓ Server is in BINARY mode (Type {msg_type})")
                        return True

            except socket.timeout:
                break
            except Exception as e:
                print(f"  Parse error: {e}")
                break

        print("✗ No valid binary response")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        with contextlib.suppress(builtins.BaseException):
            sock.close()


def test_no_encoding_negotiation():
    """Test direct LOGON without ENCODING_REQUEST."""
    print("\n" + "=" * 80)
    print("TEST 3: DIRECT JSON LOGON (No Encoding Negotiation)")
    print("=" * 80)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, PORT))
        print(f"✓ Connected to {HOST}:{PORT}")

        # Send LOGON_REQUEST directly (some servers accept this)
        logon_req = {
            "Type": 1,
            "ProtocolVersion": 8,
            "ClientName": "APPSIERRA_TEST",
            "HeartbeatIntervalInSeconds": 5,
            "Username": "",
            "Password": "",
            "TradeMode": 1,
        }
        msg = json.dumps(logon_req).encode("utf-8") + b"\x00"
        sock.send(msg)
        print(f"→ Sent LOGON_REQUEST: {logon_req}")

        # Wait for response
        buffer = b""
        start = time.time()

        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    print("✗ Server closed connection (REJECTED)")
                    return False
                buffer += chunk

                while b"\x00" in buffer:
                    idx = buffer.index(b"\x00")
                    frame = buffer[:idx]
                    buffer = buffer[idx + 1 :]

                    if frame:
                        try:
                            msg = json.loads(frame)
                            msg_type = msg.get("Type")

                            if msg_type == 2:  # LOGON_RESPONSE
                                print(f"✓ LOGON_RESPONSE received: {msg}")
                                print("✓ Server accepts direct JSON LOGON (encoding negotiation not required)!")
                                return True
                            else:
                                print(f"  Received Type {msg_type}: {msg}")
                        except json.JSONDecodeError:
                            print("✗ Invalid JSON response")
                            return False
            except socket.timeout:
                break

        print("✗ Timeout waiting for LOGON_RESPONSE")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        with contextlib.suppress(builtins.BaseException):
            sock.close()


if __name__ == "__main__":
    print("=" * 80)
    print("SIERRA CHART DTC CONFIGURATION DIAGNOSIS")
    print("=" * 80)
    print(f"Target: {HOST}:{PORT}")

    json_ok = test_json_encoding()
    binary_ok = test_binary_encoding()
    direct_ok = test_no_encoding_negotiation()

    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    print(f"JSON Encoding Negotiation:  {'✓ SUPPORTED' if json_ok else '✗ NOT SUPPORTED'}")
    print(f"Binary DTC Protocol:        {'✓ SUPPORTED' if binary_ok else '✗ NOT SUPPORTED'}")
    print(f"Direct JSON Logon:          {'✓ SUPPORTED' if direct_ok else '✗ NOT SUPPORTED'}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if json_ok:
        print("✓ Sierra Chart supports JSON encoding!")
        print("  Your app should work correctly.")
    elif direct_ok:
        print("⚠ Sierra Chart accepts JSON but skips encoding negotiation.")
        print("  SOLUTION: Skip ENCODING_REQUEST and send LOGON_REQUEST directly.")
        print("  Update your code to use --skip-encoding-request flag.")
    elif binary_ok:
        print("✗ Sierra Chart is in BINARY-ONLY mode!")
        print("  SOLUTION:")
        print("  1. Open Sierra Chart")
        print("  2. Go to: Global Settings > Data/Trade Service Settings")
        print("  3. Under 'DTC Protocol Server' section:")
        print("     - Enable 'Use JSON Encoding' or 'JSON Compact'")
        print("     - OR: Disable 'Use Binary Encoding Only'")
        print("  4. Click OK and restart Sierra Chart")
    else:
        print("✗ Cannot establish DTC connection!")
        print("  Verify Sierra Chart DTC server is running and configured.")

    print("=" * 80)
