from __future__ import annotations

import argparse
import importlib
import inspect
from pathlib import Path
import sys
import time
from typing import Any


try:
    from tools._common import DEFAULT_LOGS, add_common_args, write_csv
except Exception:
    from _common import DEFAULT_LOGS, add_common_args, write_csv

__scope__ = "diagnostics.signal_trace"


def _is_signal(obj: Any) -> bool:
    # PyQt6 bound signals typically have connect/emit
    return hasattr(obj, "connect") and hasattr(obj, "emit")


def _connect_all_signals(widget: Any, sink):
    # Best-effort: connect any bound signals on the object
    for name in dir(widget):
        try:
            attr = getattr(widget, name)
        except Exception:
            continue
        if _is_signal(attr):
            try:
                attr.connect(lambda *a, _n=name, **k: sink(_n, a, k))
            except Exception:
                pass


def trace(run_target: str, out_file: Path, duration: float) -> None:
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    rows = [("ts", "signal", "argc", "kwargs")]  # headers

    def sink(sig_name: str, args: tuple, kwargs: dict):
        rows.append((f"{time.time():.3f}", sig_name, str(len(args)), str(sorted(kwargs.keys()))))

    if ":" in run_target:
        mod_name, obj_name = run_target.split(":", 1)
        mod = importlib.import_module(mod_name)
        obj = getattr(mod, obj_name)
        if inspect.isclass(obj):
            inst = obj()
            _connect_all_signals(inst, sink)
        else:
            _connect_all_signals(obj, sink)
    else:
        # Fallback: run module
        importlib.import_module(run_target)

    deadline = time.time() + float(duration)
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    write_csv(rows[1:], rows[0], out_file)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Trace PyQt signal emissions for a widget or module")
    ap.add_argument("--run", required=True, help="Run target: module or module:ClassName")
    ap.add_argument("--duration", default=5, type=float, help="Trace duration in seconds")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_LOGS / "signal_trace.csv"))
    args = ap.parse_args(argv)

    out_path = Path(args.out)
    trace(args.run, out_path, args.duration)
    if not args.quiet:
        print(f"Signal trace written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
