"""
DTC Test Framework - Shared utilities for DTC connectivity testing

Eliminates duplication across test/diagnostic scripts by providing
reusable connection, message capture, and verification utilities.

Usage:
    from tools.dtc_test_framework import (
        DTCTestConnection,
        capture_messages,
        verify_handshake,
        print_message_summary
    )
"""

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
import json
import socket
import time
from typing import Any, Dict, List, Optional


__scope__ = "dtc.test_framework"

from config.settings import DTC_HOST, DTC_PORT, LIVE_ACCOUNT
from services.dtc_constants import (
    HEARTBEAT,
    LOGON_REQUEST,
    LOGON_RESPONSE,
    TRADE_MODE_LIVE,
    type_to_name,
)
from services.dtc_protocol import (
    build_heartbeat,
    build_logon_request,
    frame_message,
    is_logon_success,
    parse_messages,
)


class DTCTestConnection:
    """
    Reusable DTC connection context manager for testing.

    Handles socket connection, logon handshake, and graceful cleanup.

    Example:
        with DTCTestConnection() as conn:
            conn.send_message({"Type": 400})  # Trade accounts request
            messages = conn.receive_messages(duration=5)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = "",
        password: str = "",
        protocol_version: int = 8,
        trade_mode: int = TRADE_MODE_LIVE,
        timeout: float = 5.0,
    ):
        self.host = host or DTC_HOST
        self.port = port or DTC_PORT
        self.username = username
        self.password = password
        self.protocol_version = protocol_version
        self.trade_mode = trade_mode
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.logged_in = False
        self.buffer = b""

    def __enter__(self):
        """Connect and perform logon handshake."""
        self.connect()
        self.logon()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean disconnect."""
        self.disconnect()

    def connect(self) -> bool:
        """
        Establish TCP connection to DTC server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            self.connected = True
            return True
        except ConnectionRefusedError:
            print(f"[ERROR] Connection refused to {self.host}:{self.port}")
            print("[HINT] Ensure Sierra Chart DTC server is running")
            return False
        except socket.timeout:
            print(f"[ERROR] Connection timeout to {self.host}:{self.port}")
            return False
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def logon(self) -> bool:
        """
        Send LOGON_REQUEST and wait for LOGON_RESPONSE.

        Returns:
            True if logon successful, False otherwise
        """
        if not self.connected:
            return False

        # Send logon request using protocol utilities
        logon_msg = build_logon_request(
            protocol_version=self.protocol_version,
            client_name="APPSIERRA_TEST",
            heartbeat_interval=5,
            username=self.username,
            password=self.password,
            trade_mode=self.trade_mode,
        )

        if not self.send_message(logon_msg):
            return False

        # Wait for logon response
        start = time.time()
        while time.time() - start < self.timeout:
            messages = self.receive_messages(duration=0.5, max_messages=10)
            for msg in messages:
                if msg.get("Type") == LOGON_RESPONSE:
                    if is_logon_success(msg):
                        self.logged_in = True
                        return True
                    else:
                        print(f"[ERROR] Logon failed: {msg}")
                        return False

        print("[ERROR] Logon response timeout")
        return False

    def send_message(self, msg: dict) -> bool:
        """
        Send a DTC message (JSON + null terminator).

        Args:
            msg: Message dictionary with 'Type' field

        Returns:
            True if sent successfully
        """
        if not self.connected or not self.sock:
            return False

        try:
            payload = frame_message(msg)
            self.sock.send(payload)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            return False

    def receive_messages(
        self,
        duration: float = 5.0,
        max_messages: Optional[int] = None,
        filter_fn: Optional[Callable[[dict], bool]] = None,
    ) -> list[dict]:
        """
        Receive messages from DTC server for specified duration.

        Args:
            duration: How long to listen (seconds)
            max_messages: Maximum messages to collect (None = unlimited)
            filter_fn: Optional filter function (return True to include)

        Returns:
            List of received message dictionaries
        """
        if not self.connected or not self.sock:
            return []

        messages = []
        start = time.time()

        try:
            self.sock.settimeout(0.1)  # Short timeout for polling

            while time.time() - start < duration:
                if max_messages and len(messages) >= max_messages:
                    break

                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break  # Connection closed
                    self.buffer += chunk
                except socket.timeout:
                    continue  # No data available, keep polling
                except Exception:
                    break  # Connection error

                # Parse complete messages using protocol utilities
                new_messages, self.buffer = parse_messages(self.buffer)

                # Apply filter and add to results
                for msg in new_messages:
                    if filter_fn is None or filter_fn(msg):
                        messages.append(msg)

        except Exception as e:
            print(f"[ERROR] Receive error: {e}")
        finally:
            # Restore timeout
            if self.sock:
                self.sock.settimeout(self.timeout)

        return messages

    def disconnect(self):
        """Close socket connection."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False
        self.logged_in = False


# ============================================================================
# High-Level Test Utilities
# ============================================================================


def quick_connect_test(host: str = None, port: int = None) -> bool:
    """
    Quick connectivity test - just verify TCP connection works.

    Returns:
        True if connection successful
    """
    host = host or DTC_HOST
    port = port or DTC_PORT

    print(f"\n{'='*80}")
    print("DTC QUICK CONNECTIVITY TEST")
    print(f"{'='*80}\n")
    print(f"Connecting to {host}:{port}...")

    conn = DTCTestConnection(host=host, port=port)
    if conn.connect():
        print("[✓] TCP connection successful")
        conn.disconnect()
        return True
    else:
        print("[✗] TCP connection failed")
        return False


def verify_handshake(host: str = None, port: int = None, verbose: bool = True) -> bool:
    """
    Verify full logon handshake.

    Args:
        host: DTC host (defaults to config.settings.DTC_HOST)
        port: DTC port (defaults to config.settings.DTC_PORT)
        verbose: Print detailed output

    Returns:
        True if handshake successful
    """
    if verbose:
        print(f"\n{'='*80}")
        print("DTC HANDSHAKE VERIFICATION")
        print(f"{'='*80}\n")

    try:
        with DTCTestConnection(host=host, port=port) as conn:
            if conn.logged_in:
                if verbose:
                    print("[✓] Handshake successful")
                return True
            else:
                if verbose:
                    print("[✗] Handshake failed")
                return False
    except Exception as e:
        if verbose:
            print(f"[✗] Handshake error: {e}")
        return False


def capture_messages(
    duration: float = 10.0,
    filter_types: Optional[list[int]] = None,
    host: str = None,
    port: int = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Capture DTC messages for analysis.

    Args:
        duration: How long to capture (seconds)
        filter_types: List of message types to capture (None = all)
        host: DTC host
        port: DTC port
        verbose: Print progress

    Returns:
        List of captured messages
    """
    if verbose:
        print(f"\n{'='*80}")
        print("DTC MESSAGE CAPTURE")
        print(f"{'='*80}")
        print(f"Duration: {duration}s")
        if filter_types:
            print(f"Filtering types: {filter_types}")
        print(f"{'='*80}\n")

    filter_fn = None
    if filter_types:
        filter_fn = lambda msg: msg.get("Type") in filter_types

    try:
        with DTCTestConnection(host=host, port=port) as conn:
            messages = conn.receive_messages(
                duration=duration,
                filter_fn=filter_fn,
            )

            if verbose:
                print(f"\n[✓] Captured {len(messages)} messages")

            return messages

    except Exception as e:
        if verbose:
            print(f"[✗] Capture error: {e}")
        return []


def print_message_summary(messages: list[dict], show_content: bool = False):
    """
    Print summary of captured messages.

    Args:
        messages: List of message dictionaries
        show_content: Show full message content (not just count)
    """
    print(f"\n{'='*80}")
    print("MESSAGE SUMMARY")
    print(f"{'='*80}\n")

    # Count by type
    type_counts = defaultdict(int)
    for msg in messages:
        msg_type = msg.get("Type", "Unknown")
        type_counts[msg_type] += 1

    # Print sorted by type
    print(f"{'TYPE':<10} {'NAME':<35} {'COUNT':<10}")
    print(f"{'-'*10} {'-'*35} {'-'*10}")

    for msg_type in sorted(type_counts.keys(), key=lambda x: (x if isinstance(x, int) else 999, str(x))):
        type_name = type_to_name(msg_type)
        count = type_counts[msg_type]
        print(f"{msg_type!s:<10} {type_name:<35} {count:<10}")

    print(f"\nTotal messages: {len(messages)}")

    # Show content if requested
    if show_content:
        print(f"\n{'='*80}")
        print("FULL MESSAGE CONTENT")
        print(f"{'='*80}\n")
        for i, msg in enumerate(messages, 1):
            msg_type = msg.get("Type", "?")
            type_name = type_to_name(msg_type)
            print(f"[{i}] Type {msg_type} ({type_name}):")
            print(f"    {json.dumps(msg, indent=2)}")
            print()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DTC Test Framework")
    parser.add_argument("--test", choices=["connect", "handshake", "capture"], default="handshake")
    parser.add_argument("--duration", type=float, default=10.0, help="Capture duration (seconds)")
    parser.add_argument("--host", default=None, help=f"DTC host (default: {DTC_HOST})")
    parser.add_argument("--port", type=int, default=None, help=f"DTC port (default: {DTC_PORT})")
    parser.add_argument("--show-content", action="store_true", help="Show full message content")

    args = parser.parse_args()

    if args.test == "connect":
        success = quick_connect_test(args.host, args.port)
        exit(0 if success else 1)

    elif args.test == "handshake":
        success = verify_handshake(args.host, args.port)
        exit(0 if success else 1)

    elif args.test == "capture":
        messages = capture_messages(
            duration=args.duration,
            host=args.host,
            port=args.port,
        )
        print_message_summary(messages, show_content=args.show_content)
        exit(0 if messages else 1)
