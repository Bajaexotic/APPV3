#!/usr/bin/env python3
"""
services/dtc_report_cli.py

CLI tool for building DTC order ledgers, snapshots, and fill streams.
Python replacement for PowerShell dtc_build_ledgers.ps1

Usage:
    python -m services.dtc_report_cli --input dtc_live_orders.jsonl --output-dir reports/
    python -m services.dtc_report_cli --input logs/dtc.jsonl --format json

Examples:
    # Generate all 3 CSV reports
    python -m services.dtc_report_cli --input logs/dtc_live_orders.jsonl

    # Generate JSON output
    python -m services.dtc_report_cli --input logs/dtc.jsonl --format json

    # Custom output directory
    python -m services.dtc_report_cli --input logs/dtc.jsonl --output-dir ~/reports/
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from services.dtc_ledger import (
    OrderLedgerBuilder,
    export_to_csv,
    export_to_json,
    read_dtc_jsonl,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build DTC order ledgers from Type 301 OrderUpdate messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input logs/dtc_live_orders.jsonl
  %(prog)s --input logs/dtc.jsonl --format json
  %(prog)s --input logs/dtc.jsonl --output-dir ~/reports/
        """,
    )

    parser.add_argument(
        "--input", "-i", required=True, help="Path to input JSONL file containing DTC Type 301 messages"
    )

    parser.add_argument(
        "--output-dir", "-o", default=".", help="Output directory for generated reports (default: current directory)"
    )

    parser.add_argument(
        "--format", "-f", choices=["csv", "json"], default="csv", help="Output format: csv or json (default: csv)"
    )

    parser.add_argument(
        "--ledger-only", action="store_true", help="Only generate order ledger summary (skip snapshot and fills)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Reading DTC messages from: {args.input}")

    try:
        # Read JSONL
        updates = read_dtc_jsonl(str(input_path))

        if not updates:
            print("[WARN] No Type 301 (OrderUpdate) messages found in input file")
            sys.exit(0)

        print(f"[INFO] Found {len(updates)} Type 301 messages")

        # Build ledger
        builder = OrderLedgerBuilder(updates)

        # Count unique orders
        unique_orders = len(builder.grouped)
        print(f"[INFO] Grouped into {unique_orders} unique orders (by ServerOrderID)")

        # Generate reports
        ext = args.format

        # 1. Order Ledger Summary
        print("\n[1/3] Building order ledger summary...")
        ledger = builder.build_ledger()
        ledger_path = output_dir / f"dtc_order_ledger_summary.{ext}"

        if ext == "csv":
            export_to_csv(ledger, str(ledger_path))
        else:
            export_to_json(ledger, str(ledger_path))

        if args.ledger_only:
            print("\n[DONE] Ledger-only mode - skipping snapshot and fills")
            return

        # 2. Latest Snapshot
        print("\n[2/3] Building latest snapshot...")
        snapshot = builder.build_snapshot()
        snapshot_path = output_dir / f"dtc_order_snapshot_latest.{ext}"

        if ext == "csv":
            export_to_csv(snapshot, str(snapshot_path))
        else:
            export_to_json(snapshot, str(snapshot_path))

        # 3. Fill Stream
        print("\n[3/3] Building fill stream...")
        fills = builder.build_fill_stream()
        fills_path = output_dir / f"dtc_fills.{ext}"

        if ext == "csv":
            export_to_csv(fills, str(fills_path))
        else:
            export_to_json(fills, str(fills_path))

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"  Input:   {args.input}")
        print(f"  Output:  {output_dir}/")
        print(f"  Format:  {ext.upper()}")
        print(f"  Orders:  {unique_orders}")
        print(f"  Fills:   {len(fills)}")
        print("=" * 60)
        print("\nFiles generated:")
        print(f"  - {ledger_path.name}")
        print(f"  - {snapshot_path.name}")
        print(f"  - {fills_path.name}")
        print("\n[DONE] ✓ All reports generated successfully")

    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
