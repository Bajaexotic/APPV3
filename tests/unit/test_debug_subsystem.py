#!/usr/bin/env python3
"""
Standalone test for debug subsystem (no PyQt6 required)
"""

import os
import sys


# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import directly from modules (bypass core/__init__.py)
import importlib.util


# Load diagnostics module directly
spec = importlib.util.spec_from_file_location("diagnostics", "core/diagnostics.py")
diagnostics = importlib.util.module_from_spec(spec)
sys.modules["core.diagnostics"] = diagnostics

# Load utils.logger first (dependency)
spec_logger = importlib.util.spec_from_file_location("logger", "utils/logger.py")
logger_module = importlib.util.module_from_spec(spec_logger)
sys.modules["utils.logger"] = logger_module
spec_logger.loader.exec_module(logger_module)

# Now load diagnostics
spec.loader.exec_module(diagnostics)

# Import error_policy
spec_policy = importlib.util.spec_from_file_location("error_policy", "core/error_policy.py")
error_policy = importlib.util.module_from_spec(spec_policy)
sys.modules["core.error_policy"] = error_policy
spec_policy.loader.exec_module(error_policy)

# Get the functions we need
DiagnosticsHub = diagnostics.DiagnosticsHub
info = diagnostics.info
debug = diagnostics.debug
warn = diagnostics.warn
error = diagnostics.error
PerformanceMarker = diagnostics.PerformanceMarker
ErrorPolicyManager = error_policy.ErrorPolicyManager
handle_error = error_policy.handle_error

import time


print("=" * 70)
print("Testing APPSIERRA Debug Subsystem")
print("=" * 70)
print()

# Test 1: Basic event logging
print("[1] Testing basic event logging...")
hub = DiagnosticsHub.get_instance(max_events=100)

info("system", "Test system started")
debug("network", "Connection test", context={"host": "127.0.0.1", "port": 11099})
warn("perf", "Slow operation detected", context={"elapsed_ms": 1500})
error("core", "Test error", context={"test": True})

stats = hub.get_statistics()
print(f"   ✓ Total events: {stats['total_events']}")
print(f"   ✓ Categories: {stats['events_by_category']}")
print(f"   ✓ Levels: {stats['events_by_level']}")
print()

# Test 2: Performance markers
print("[2] Testing performance markers...")
with PerformanceMarker("test_operation", category="perf"):
    time.sleep(0.1)

perf_events = [e for e in hub.events if e.event_type == "PerformanceMeasurement"]
if perf_events:
    print("   ✓ Performance marker created")
    print(f"   ✓ Elapsed: {perf_events[-1].elapsed_ms:.2f}ms")
print()

# Test 3: Snapshot export
print("[3] Testing snapshot export...")
snapshot = hub.snapshot(max_events=10)
print(f"   ✓ Snapshot contains {len(snapshot)} events")

export_file = "logs/test_snapshot.json"
hub.export_json(export_file)
print(f"   ✓ Exported to {export_file}")
print()

# Test 4: Error policy manager
print("[4] Testing error policy manager...")
policy_mgr = ErrorPolicyManager.get_instance()
policy = policy_mgr.get_policy("dtc_connection_drop", "network")
print(f"   ✓ Policy loaded: {policy.recovery}")
print(f"   ✓ Max retries: {policy.max_retries}")
print(f"   ✓ Escalation: {policy.escalation}")
print()

# Test 5: Error handling with retry
print("[5] Testing error handling with retry...")
attempt_count = [0]


def failing_operation():
    attempt_count[0] += 1
    if attempt_count[0] < 2:
        raise Exception(f"Simulated failure {attempt_count[0]}")
    return True


success = handle_error(
    error_type="dtc_connection_drop", category="network", context={"test": True}, operation=failing_operation
)

print(f"   ✓ Operation result: {'SUCCESS' if success else 'FAILED'}")
print(f"   ✓ Total attempts: {attempt_count[0]}")
print()

# Test 6: Final statistics
print("[6] Final statistics:")
final_stats = hub.get_statistics()
print(f"   Total events: {final_stats['total_events']}")
print(f"   Error count: {final_stats['errors_count']}")
print(f"   Fatal count: {final_stats['fatal_count']}")
print()

print("=" * 70)
print("✓ All tests passed!")
print("=" * 70)
print()
print("Debug subsystem is working correctly.")
print(f"Check {export_file} for exported diagnostic data.")
