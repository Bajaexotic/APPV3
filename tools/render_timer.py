from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys
import time
from typing import Any, List


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "performance.render_timer"


def measure_paint(widget: Any, duration: float) -> dict:
    from PyQt6 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    intervals: list[float] = []

    orig = getattr(widget, "paintEvent", None)

    def wrapped(ev):
        nonlocal last
        now = time.perf_counter()
        if last is not None:
            intervals.append((now - last) * 1000.0)
        if orig:
            orig(ev)
        last = time.perf_counter()

    last = None
    if orig:
        setattr(widget, "paintEvent", wrapped)

    widget.show()
    deadline = time.time() + duration
    while time.time() < deadline:
        widget.update()
        app.processEvents()
        time.sleep(0.01)

    if intervals:
        avg = sum(intervals) / len(intervals)
    else:
        avg = 0.0
    return {"samples": len(intervals), "avg_ms": round(avg, 3)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Measure repaint intervals for a widget")
    ap.add_argument("--widget", required=True, help="Target widget as module:Class")
    ap.add_argument("--duration", type=float, default=3, help="Duration in seconds")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "render_timer.json"))
    args = ap.parse_args(argv)

    mod_name, cls_name = args.widget.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    w = cls()
    report = measure_paint(w, float(args.duration))
    out_path = Path(args.out)
    write_json(report, out_path)
    print(f"Render timer written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
