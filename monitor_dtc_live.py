#!/usr/bin/env python3
"""
Live DTC Message Monitor
Tails the app log in real-time and highlights DTC messages as they arrive.
Run this in parallel with: python main.py DEBUG_DTC=1 DEBUG_DATA=1
"""

import builtins
from collections import defaultdict
import contextlib
from pathlib import Path
import re
import subprocess
import sys


def monitor_logs(log_file="logs/app.log", follow_delay=0.5):
    """Monitor logs in real-time and highlight DTC messages"""
    log_path = Path(log_file)

    if not log_path.exists():
        print(f"✗ Log file not found: {log_path}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print("DTC MESSAGE MONITOR")
    print(f"{'='*80}")
    print(f"Monitoring: {log_path}")
    print("Press Ctrl+C to stop\n")

    message_counts = defaultdict(int)

    # Use tail -f equivalent with Python
    try:
        process = subprocess.Popen(
            ["powershell", "-Command", f"Get-Content -Path {log_path} -Tail 50 -Wait"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            if not line:
                break

            line = line.rstrip()

            # Highlight DTC messages
            if "[DTC" in line or "dtc." in line or "balance" in line.lower():
                # Parse message type
                type_match = re.search(r"Type[:\s]+(\d+)", line)
                name_match = re.search(r"\(([^)]*)\)", line)

                type_num = type_match.group(1) if type_match else "?"
                type_name = name_match.group(1) if name_match else "?"

                # Color code by type
                if type_num == "2":
                    prefix = "→ LOGON_RESPONSE"
                    color = "\033[92m"  # Green
                elif type_num == "600" or type_num == "602":
                    prefix = "→ BALANCE"
                    color = "\033[94m"  # Blue
                    message_counts["BALANCE"] += 1
                elif type_num == "306":
                    prefix = "→ POSITION"
                    color = "\033[93m"  # Yellow
                    message_counts["POSITION"] += 1
                elif type_num == "301":
                    prefix = "→ ORDER"
                    color = "\033[95m"  # Magenta
                    message_counts["ORDER"] += 1
                elif type_num in ("400", "401"):
                    prefix = "→ ACCOUNTS"
                    color = "\033[96m"  # Cyan
                    message_counts["ACCOUNTS"] += 1
                elif "request" in line.lower():
                    prefix = "→ REQUEST"
                    color = "\033[97m"  # White
                    message_counts["REQUEST"] += 1
                else:
                    prefix = f"→ Type {type_num}"
                    color = "\033[0m"  # Normal

                reset = "\033[0m"

                print(f"{color}[{prefix}]{reset} {line}")

                # Show summary occasionally
                if sum(message_counts.values()) % 10 == 0:
                    print("\n📊 Message Summary:")
                    for msg_type, count in sorted(message_counts.items()):
                        print(f"   {msg_type}: {count}")
                    print()

            # Also show connection status
            elif "DTC connected" in line:
                print(f"\033[92m✓ DTC Connected\033[0m {line}")
            elif "DTC disconnected" in line:
                print(f"\033[91m✗ DTC Disconnected\033[0m {line}")
            elif "error" in line.lower():
                print(f"\033[91m✗ Error\033[0m {line}")

    except KeyboardInterrupt:
        print(f"\n{'='*80}")
        print("Monitoring stopped")
        print(f"{'='*80}")
        print("\nFinal Message Summary:")
        for msg_type, count in sorted(message_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {msg_type}: {count}")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        with contextlib.suppress(builtins.BaseException):
            process.terminate()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor DTC messages in app logs")
    parser.add_argument("--log", default="logs/app.log", help="Log file to monitor")
    args = parser.parse_args()

    monitor_logs(args.log)
