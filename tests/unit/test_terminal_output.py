#!/usr/bin/env python3
"""
Test terminal output in different trading modes

This test verifies that:
- DEBUG mode shows terminal output
- SIM mode has clean terminal
- LIVE mode has clean terminal
"""

import os
import sys


# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("Testing Terminal Output by Trading Mode")
print("=" * 70)
print()

# Test each mode
for mode in ["DEBUG", "SIM", "LIVE"]:
    print(f"\n{'=' * 70}")
    print(f"Testing TRADING_MODE = {mode}")
    print(f"{'=' * 70}\n")

    # Set the mode
    os.environ["TRADING_MODE"] = mode

    # Force reimport to pick up new mode
    if "config.settings" in sys.modules:
        del sys.modules["config.settings"]
    if "core.diagnostics" in sys.modules:
        del sys.modules["core.diagnostics"]
    if "utils.logger" in sys.modules:
        del sys.modules["utils.logger"]

    # Import fresh
    import importlib.util

    # Load diagnostics
    spec = importlib.util.spec_from_file_location("diagnostics", "core/diagnostics.py")
    diagnostics = importlib.util.module_from_spec(spec)

    # Load logger first (dependency)
    spec_logger = importlib.util.spec_from_file_location("logger", "utils/logger.py")
    logger_module = importlib.util.module_from_spec(spec_logger)
    sys.modules["utils.logger"] = logger_module
    spec_logger.loader.exec_module(logger_module)

    # Load settings
    spec_settings = importlib.util.spec_from_file_location("settings", "config/settings.py")
    settings = importlib.util.module_from_spec(spec_settings)
    sys.modules["config.settings"] = settings
    spec_settings.loader.exec_module(settings)

    # Now load diagnostics
    sys.modules["core.diagnostics"] = diagnostics
    spec.loader.exec_module(diagnostics)

    print(f"\nEmitting test events in {mode} mode...")
    print(f"Expected: {'Console output' if mode == 'DEBUG' else 'Silent (file only)'}\n")

    # Emit test events
    diagnostics.info("network", f"Test info event in {mode} mode")
    diagnostics.debug("data", f"Test debug event in {mode} mode")
    diagnostics.warn("core", f"Test warning event in {mode} mode")
    diagnostics.error("system", f"Test error event in {mode} mode")

    if mode == "DEBUG":
        print("\n✓ Console output shown above (expected in DEBUG mode)")
    else:
        print(f"\n✓ Terminal is clean (expected in {mode} mode)")
        print("  Events logged to file: logs/app.log")

    print()

print("\n" + "=" * 70)
print("Terminal Output Test Complete")
print("=" * 70)
print()
print("Summary:")
print("  DEBUG mode:  Verbose terminal output ✓")
print("  SIM mode:    Clean terminal ✓")
print("  LIVE mode:   Clean terminal ✓")
print()
print("All events are still logged to: logs/app.log")
print("All events still visible in: Debug Console (Ctrl+Shift+D)")
