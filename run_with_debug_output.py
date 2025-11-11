#!/usr/bin/env python
"""
Wrapper script to run the main application and capture all output to a log file.
This allows us to see all print() and log statements in the GUI application.
"""
import sys
import os

# Redirect stdout and stderr to both console and file
output_file = r"C:\Users\cgrah\OneDrive\Desktop\APPSIERRA\debug_output.log"

class TeeOutput:
    def __init__(self, name, *files):
        self.name = name
        self.files = files

    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()

# Open log file
log_file = open(output_file, 'w')

# Redirect stdout and stderr
sys.stdout = TeeOutput('stdout', sys.stdout, log_file)
sys.stderr = TeeOutput('stderr', sys.stderr, log_file)

print(f"[INIT] Starting application with debug output to {output_file}")
print(f"[INIT] Python: {sys.executable}")
print(f"[INIT] Version: {sys.version}")

# Now import and run main
try:
    from main import main
    print("[INIT] main module imported successfully")
    main()
except Exception as e:
    print(f"[ERROR] Failed to run main: {e}")
    import traceback
    traceback.print_exc()
finally:
    log_file.close()
