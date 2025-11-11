from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "performance.startup_profiler"


def time_construct(target: str) -> float:
    """
    Measure construction time for a class.

    Args:
        target: Import path like "module:ClassName"

    Returns:
        Construction time in milliseconds
    """
    mod_name, cls_name = target.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    t0 = time.perf_counter()
    obj = cls()
    # Qt widgets: try to close on cleanup
    try:
        from PyQt6 import QtWidgets

        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    except Exception:
        pass
    return (time.perf_counter() - t0) * 1000.0


def bench_sqlite(rows: int = 10000) -> dict:
    """
    Benchmark basic SQLite operations (insert, query, delete).

    Args:
        rows: Number of rows to insert/operate on

    Returns:
        Dict with timing results in milliseconds
    """
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("create table t (id integer primary key, v text)")

    # Insert benchmark
    t0 = time.perf_counter()
    cur.executemany("insert into t (v) values (?)", [(f"v{i}",) for i in range(rows)])
    conn.commit()
    t_ins = (time.perf_counter() - t0) * 1000.0

    # Query benchmark
    t0 = time.perf_counter()
    cur.execute("select count(*) from t where id > ?", (rows // 2,))
    cur.fetchone()
    t_q = (time.perf_counter() - t0) * 1000.0

    # Delete benchmark
    t0 = time.perf_counter()
    cur.execute("delete from t where id % 2 = 0")
    conn.commit()
    t_del = (time.perf_counter() - t0) * 1000.0

    conn.close()

    return {"insert_ms": round(t_ins, 2), "query_ms": round(t_q, 2), "delete_ms": round(t_del, 2), "rows": rows}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Profile startup/construct times and database performance")
    ap.add_argument("--targets", nargs="+", help="List like module:Class")
    ap.add_argument("--bench-db", action="store_true", help="Run database benchmark")
    ap.add_argument("--db-rows", type=int, default=10000, help="Rows for DB benchmark")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "startup_timings.json"))
    args = ap.parse_args(argv)

    results = {}

    # Ensure Qt app exists if needed
    if args.targets:
        try:
            from PyQt6 import QtWidgets

            _ = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        except Exception:
            pass

        # Profile class construction times
        for t in args.targets:
            try:
                ms = time_construct(t)
                results[t] = {"ms": round(ms, 3)}
            except Exception as e:
                results[t] = {"error": str(e)}

    # Run database benchmark if requested
    if args.bench_db:
        try:
            db_results = bench_sqlite(args.db_rows)
            results["db_benchmark"] = db_results
            if not args.quiet:
                print(f"DB Benchmark ({args.db_rows} rows):")
                print(f"  Insert: {db_results['insert_ms']} ms")
                print(f"  Query:  {db_results['query_ms']} ms")
                print(f"  Delete: {db_results['delete_ms']} ms")
        except Exception as e:
            results["db_benchmark"] = {"error": str(e)}

    if not results:
        print("Error: Specify --targets and/or --bench-db")
        return 1

    out_path = Path(args.out)
    write_json(results, out_path)
    if not args.quiet:
        print(f"✅ Performance timings written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
