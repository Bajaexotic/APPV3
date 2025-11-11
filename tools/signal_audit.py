#!/usr/bin/env python3
"""
Signal Audit Harness for Blinker Signals

Purpose:
    Audit all Blinker signals in the application to show:
    - How many receivers each signal has
    - Fully qualified name of each receiver
    - Which modules own those receivers

    This provides a "before surgery" baseline for architectural refactoring.

Usage:
    # Run as standalone script:
    python tools/signal_audit.py

    # Run with detailed output:
    python tools/signal_audit.py --verbose

    # Run as pytest:
    pytest tools/signal_audit.py::test_signal_audit

    # Enable at app startup (add to app_manager.py or main.py):
    if os.getenv("DEBUG_SIGNAL_AUDIT") == "1":
        from tools.signal_audit import audit_all_signals
        audit_all_signals()
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import inspect
from pathlib import Path
import sys
from typing import Any


try:
    from tools._common import DEFAULT_LOGS, add_common_args, write_csv
except Exception:
    from _common import DEFAULT_LOGS, add_common_args, write_csv


__scope__ = "diagnostics.signal_audit"


def get_callable_name(func: Callable) -> str:
    """
    Extract fully qualified name from a callable.

    Examples:
        function → module.function_name
        method → module.ClassName.method_name
        lambda → module.<lambda at file.py:123>
    """
    try:
        # Handle bound methods
        if hasattr(func, "__self__") and hasattr(func, "__func__"):
            cls = func.__self__.__class__
            module = cls.__module__
            class_name = cls.__qualname__
            method_name = func.__func__.__name__
            return f"{module}.{class_name}.{method_name}"

        # Handle regular functions
        if hasattr(func, "__module__") and hasattr(func, "__qualname__"):
            return f"{func.__module__}.{func.__qualname__}"

        # Handle lambdas with file info
        if hasattr(func, "__code__"):
            code = func.__code__
            filename = Path(code.co_filename).name
            lineno = code.co_firstlineno
            return f"{func.__module__}.<lambda at {filename}:{lineno}>"

        # Fallback
        return repr(func)
    except Exception as e:
        return f"<unknown: {e}>"


def get_receiver_info(receiver: Any) -> dict[str, str]:
    """
    Extract detailed info about a Blinker receiver.

    Returns:
        dict with keys: name, module, file, line
    """
    try:
        name = get_callable_name(receiver)

        # Extract module name
        if hasattr(receiver, "__self__"):
            module = receiver.__self__.__class__.__module__
        elif hasattr(receiver, "__module__"):
            module = receiver.__module__
        else:
            module = "unknown"

        # Extract file location
        try:
            source_file = inspect.getsourcefile(receiver) or "unknown"
            source_file = str(Path(source_file).relative_to(Path.cwd()))
        except Exception:
            source_file = "unknown"

        # Extract line number
        try:
            lineno = inspect.getsourcelines(receiver)[1]
        except Exception:
            lineno = -1

        return {"name": name, "module": module, "file": source_file, "line": str(lineno) if lineno > 0 else "unknown"}
    except Exception as e:
        return {"name": f"<error: {e}>", "module": "unknown", "file": "unknown", "line": "unknown"}


def audit_signal(signal_name: str, signal_obj: Any, verbose: bool = False) -> dict:
    """
    Audit a single Blinker signal.

    Returns:
        dict with keys: signal_name, receiver_count, receivers (list of dicts)
    """
    try:
        # Blinker signals have a .receivers attribute (dict-like or set-like)
        receivers = getattr(signal_obj, "receivers", {})

        # Convert to list of callables
        if isinstance(receivers, dict):
            receiver_list = list(receivers.keys())
        else:
            receiver_list = list(receivers)

        receiver_count = len(receiver_list)

        # Extract detailed info for each receiver
        receiver_details = [get_receiver_info(r) for r in receiver_list]

        return {"signal_name": signal_name, "receiver_count": receiver_count, "receivers": receiver_details}
    except Exception as e:
        return {"signal_name": signal_name, "receiver_count": 0, "receivers": [], "error": str(e)}


def audit_all_signals(verbose: bool = False) -> list[dict]:
    """
    Audit all Blinker signals in the application.

    NOTE: This requires the full application environment (PyQt6, etc.)
          Run inside your virtual environment where the app runs.

    Returns:
        List of audit results (one per signal)
    """
    results = []

    try:
        # Import Blinker signals from data_bridge
        # This requires PyQt6 and other dependencies to be available
        from core.data_bridge import (
            signal_balance,
            signal_order,
            signal_position,
            signal_trade_account,
        )

        signals_to_audit = [
            ("signal_balance", signal_balance),
            ("signal_order", signal_order),
            ("signal_position", signal_position),
            ("signal_trade_account", signal_trade_account),
        ]

        for signal_name, signal_obj in signals_to_audit:
            result = audit_signal(signal_name, signal_obj, verbose)
            results.append(result)

    except ModuleNotFoundError as e:
        print(f"\nERROR: Missing dependency - {e}", file=sys.stderr)
        print("\nThis tool requires the full application environment.", file=sys.stderr)
        print("Please run inside your virtual environment:", file=sys.stderr)
        print("  source .venv/bin/activate  # or: .venv\\Scripts\\activate on Windows", file=sys.stderr)
        print("  python tools/signal_audit.py --verbose\n", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to import signals: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    return results


def print_audit_results(results: list[dict], verbose: bool = False) -> None:
    """Print audit results in human-readable format."""
    print("\n" + "=" * 80)
    print("BLINKER SIGNAL AUDIT REPORT")
    print("=" * 80 + "\n")

    for result in results:
        signal_name = result["signal_name"]
        receiver_count = result["receiver_count"]
        receivers = result.get("receivers", [])
        error = result.get("error")

        print(f"Signal: {signal_name}")
        print(f"  Receiver Count: {receiver_count}")

        if error:
            print(f"  ERROR: {error}")

        if receivers:
            print("  Receivers:")
            for i, receiver in enumerate(receivers, 1):
                print(f"    [{i}] {receiver['name']}")
                if verbose:
                    print(f"        Module: {receiver['module']}")
                    print(f"        File:   {receiver['file']}:{receiver['line']}")
        else:
            print("  (no receivers)")

        print()

    # Summary
    total_signals = len(results)
    total_receivers = sum(r["receiver_count"] for r in results)
    print("=" * 80)
    print(f"SUMMARY: {total_signals} signals, {total_receivers} total receivers")
    print("=" * 80 + "\n")


def export_to_csv(results: list[dict], out_file: Path) -> None:
    """Export audit results to CSV for analysis."""
    rows = []
    headers = ("signal", "receiver_count", "receiver_name", "receiver_module", "receiver_file", "receiver_line")

    for result in results:
        signal_name = result["signal_name"]
        receiver_count = result["receiver_count"]
        receivers = result.get("receivers", [])

        if not receivers:
            # Add a row even if no receivers
            rows.append((signal_name, str(receiver_count), "", "", "", ""))
        else:
            for receiver in receivers:
                rows.append(
                    (
                        signal_name,
                        str(receiver_count),
                        receiver["name"],
                        receiver["module"],
                        receiver["file"],
                        receiver["line"],
                    )
                )

    write_csv(rows, headers, out_file)


def main(argv: list[str]) -> int:
    """Main entry point for CLI usage."""
    ap = argparse.ArgumentParser(
        description="Audit Blinker signals to show receiver counts and connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--verbose", "-v", action="store_true", help="Show detailed receiver info")
    ap.add_argument("--csv", action="store_true", help="Export results to CSV")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_LOGS / "signal_audit.csv"))
    args = ap.parse_args(argv)

    # Run audit
    results = audit_all_signals(verbose=args.verbose)

    # Print results (unless quiet)
    if not args.quiet:
        print_audit_results(results, verbose=args.verbose)

    # Export to CSV if requested
    if args.csv:
        out_path = Path(args.out)
        export_to_csv(results, out_path)
        if not args.quiet:
            print(f"CSV export written to {out_path}")

    # Return non-zero if any signal has multiple receivers (indicates redundancy)
    has_redundancy = any(r["receiver_count"] > 1 for r in results)
    return 1 if has_redundancy else 0


# -------------------- Pytest integration --------------------


def test_signal_audit():
    """
    Pytest test that runs signal audit and asserts architectural invariants.

    Usage:
        pytest tools/signal_audit.py::test_signal_audit
    """
    results = audit_all_signals(verbose=True)

    # Assert: we found all expected signals
    signal_names = {r["signal_name"] for r in results}
    expected_signals = {
        "signal_balance",
        "signal_order",
        "signal_position",
        "signal_trade_account",
    }
    assert signal_names == expected_signals, f"Missing signals: {expected_signals - signal_names}"

    # Print results for manual inspection
    print_audit_results(results, verbose=True)

    # Note: After refactoring, you can add assertions like:
    # for result in results:
    #     assert result["receiver_count"] <= 1, f"{result['signal_name']} has {result['receiver_count']} receivers (expected 1)"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
