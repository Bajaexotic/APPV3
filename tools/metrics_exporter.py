from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_csv, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_csv, write_json

__scope__ = "reporting.metrics_exporter"


def gather(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for base in paths:
        if not base.exists():
            continue
        for root, _, files in os.walk(base):
            for f in files:
                p = Path(root) / f
                if f.lower().endswith((".json", ".csv", ".log")):
                    rows.append({"file": str(p), "size": p.stat().st_size})
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Aggregate tool outputs (logs/reports) into a summary")
    ap.add_argument("--inputs", nargs="+", default=["reports", "logs"], help="Directories to scan")
    ap.add_argument("--csv", action="store_true", help="Also write CSV summary")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "metrics_summary.json"))
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    paths = [repo / Path(x) for x in args.inputs]
    rows = gather(paths)
    out_path = Path(args.out)
    write_json(rows, out_path)
    if args.csv:
        csv_path = out_path.with_suffix(".csv")
        write_csv(((r["file"], r["size"]) for r in rows), ("file", "size"), csv_path)
        print(f"Metrics CSV written: {csv_path}")
    print(f"Metrics summary written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
