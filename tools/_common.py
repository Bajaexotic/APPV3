from __future__ import annotations

import argparse
from collections.abc import Iterable
import csv
from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS = REPO_ROOT / "logs"
DEFAULT_REPORTS = REPO_ROOT / "reports"


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(data: Any, out_path: Path) -> None:
    ensure_dir(out_path)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_csv(rows: Iterable[Iterable[Any]], headers: Optional[Iterable[str]], out_path: Path) -> None:
    ensure_dir(out_path)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if headers:
            w.writerow(list(headers))
        for r in rows:
            w.writerow(list(r))


def parse_kv_file(path: Path) -> dict:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def snake_to_module(path: str) -> str:
    return path.replace("/", ".").replace("\\", ".").rstrip(".py")


def is_color_token(s: str) -> bool:
    """
    DEPRECATED: Use tools.theme_validation.is_color_token instead.
    Kept for backward compatibility.
    """
    try:
        from tools.theme_validation import is_color_token as _is_color_token

        return _is_color_token(s)
    except ImportError:
        # Fallback implementation
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", s):
            return True
        if s.lower().startswith("oklch(") and s.endswith(")"):
            return True
        return False


def dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [dataclass_to_dict(v) for v in obj]
    return obj


def add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=str, help="Output file path (JSON/CSV depending on tool)")
    p.add_argument("--quiet", action="store_true", help="Reduce console output")


def exit_with_message(ok: bool, msg: str) -> None:
    print(msg)
    sys.exit(0 if ok else 1)
