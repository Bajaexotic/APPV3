#!/usr/bin/env python3
"""
Run the APPSIERRA app and capture ALL console output to a file.

Usage:
    python run_app_with_logging.py

This will:
1. Start the app
2. Capture all print() and logging output
3. Save to: terminal_log.txt
4. Display output on screen too (so you can see it happening)

After closing trades, the log file will have everything!
"""

import subprocess
import sys
import os
from datetime import datetime

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, "terminal_log.txt")

print(f"Starting APPSIERRA with logging...")
print(f"Log file: {log_file}")
print(f"=" * 100)
print(f"Close trades and watch the output below!")
print(f"=" * 100)

# Write header to log file
with open(log_file, "w") as f:
    f.write(f"APPSIERRA Terminal Log\n")
    f.write(f"Started: {datetime.now()}\n")
    f.write(f"=" * 100 + "\n\n")

# Run the app and capture output
try:
    # Use 'python main.py' and pipe output to both console and file
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=script_dir,
        bufsize=1  # Line buffered
    )

    # Read output line by line
    with open(log_file, "a") as f:
        for line in process.stdout:
            # Print to console
            print(line, end="", flush=True)
            # Write to file
            f.write(line)
            f.flush()

    # Wait for process to finish
    process.wait()

except Exception as e:
    print(f"ERROR: Could not start app: {e}")
    sys.exit(1)

print(f"\n" + "=" * 100)
print(f"App closed.")
print(f"Log saved to: {log_file}")
print(f"=" * 100)
