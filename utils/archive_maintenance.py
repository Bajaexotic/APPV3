from __future__ import annotations

from collections.abc import Iterable
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple


DB_GLOBS: tuple[str, ...] = (
    "*.db",
    "pnl_data_*.db",
    "archive_*.db",
)


def find_sqlite_archives(root: os.PathLike[str] | str, patterns: Iterable[str] = DB_GLOBS) -> list[Path]:
    base = Path(root)
    if not base.exists():
        return []
    found: list[Path] = []
    for pat in patterns:
        found.extend(base.rglob(pat))
    # Deduplicate while preserving order
    seen = set()
    uniq: list[Path] = []
    for p in found:
        if p.suffix.lower() != ".db":
            continue
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def file_size_mb(path: os.PathLike[str] | str) -> float:
    try:
        return max(0.0, Path(path).stat().st_size / (1024 * 1024))
    except OSError:
        return 0.0


def vacuum_sqlite_db(path: os.PathLike[str] | str) -> bool:
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.isolation_level = None  # autocommit for VACUUM
            conn.execute("VACUUM;")
        return True
    except Exception:
        return False


def optimize_archives(root: os.PathLike[str] | str, threshold_mb: float = 200.0) -> dict[str, object]:
    """
    Scan for .db archives under `root` and VACUUM them.
    Returns a summary dict with before/after sizes and which files were optimized.
    """
    root = Path(root)
    dbs = find_sqlite_archives(root)
    summary: dict[str, object] = {"root": str(root), "optimized": [], "skipped": []}
    for db in dbs:
        before = file_size_mb(db)
        ok = vacuum_sqlite_db(db)
        after = file_size_mb(db)
        entry = {"path": str(db), "before_mb": before, "after_mb": after, "ok": ok}
        if ok:
            summary["optimized"].append(entry)  # type: ignore[index]
        else:
            summary["skipped"].append(entry)  # type: ignore[index]
    # Flag large files after optimization
    summary["oversized_after_mb"] = [e for e in summary.get("optimized", []) if e.get("after_mb", 0) > threshold_mb]  # type: ignore[union-attr]
    return summary


# UI helper (optional)
def optimize_archives_with_prompt(
    root: os.PathLike[str] | str, threshold_mb: float = 200.0, parent=None
) -> dict[str, object]:
    """Qt-aware helper that prompts when any DB exceeds `threshold_mb` before/after.
    Safe to call from UI; avoids raising on failure.
    """
    try:
        from PyQt6 import QtWidgets
    except Exception:  # pragma: no cover
        return optimize_archives(root, threshold_mb)

    dbs = find_sqlite_archives(root)
    big = [p for p in dbs if file_size_mb(p) > threshold_mb]
    proceed = True
    if big:
        msg = QtWidgets.QMessageBox(parent)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msg.setWindowTitle("Optimize Archives")
        lines = [f"{p.name} — {file_size_mb(p):.1f} MB" for p in big]
        msg.setText("Some archives exceed the size threshold. Vacuum now?\n" + "\n".join(lines))
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        proceed = msg.exec() == int(QtWidgets.QMessageBox.StandardButton.Yes)
    if not proceed:
        return {"root": str(root), "optimized": [], "skipped": [], "oversized_after_mb": []}

    summary = optimize_archives(root, threshold_mb)

    # Show small completion toast
    try:
        msg = QtWidgets.QMessageBox(parent)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msg.setWindowTitle("Optimize Archives")
        ok_count = len(summary.get("optimized", []))
        msg.setText(f"Vacuum complete. Optimized {ok_count} archive(s).")
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg.exec()
    except Exception:
        pass
    return summary
