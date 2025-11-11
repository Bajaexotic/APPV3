from __future__ import annotations

import json

# File: core/persistence.py
# Block 29/?? Ã¢â‚¬â€ JSONL and cache helpers
import os
import time
from typing import Any, Dict, List, Optional

from utils.logger import get_logger


log = get_logger(__name__)


# ---- Cache directory management ----
def ensure_cache_dir() -> str:
    """Ensure that ~/.sierra_pnl_monitor exists."""
    path = os.path.expanduser("~/.sierra_pnl_monitor")
    os.makedirs(path, exist_ok=True)
    return path


# ---- JSONL (line-delimited JSON) helpers ----
def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    data: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except Exception:
                continue
    return data


def append_jsonl(path: str, obj: dict) -> None:
    ensure_cache_dir()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


# ---- Simple key-value JSON cache ----
def append_cache(key: str, value: Any) -> None:
    path = os.path.join(ensure_cache_dir(), f"{key}.json")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append({"ts": time.time(), "value": value})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
    except Exception as e:
        log.error(f"Failed to append cache {key}: {e}")


def read_cache_between(key: str, t_start: float, t_end: float) -> list[dict]:
    path = os.path.join(ensure_cache_dir(), f"{key}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [d for d in data if t_start <= d.get("ts", 0) <= t_end]
    except Exception as e:
        log.error(f"Error reading cache {key}: {e}")
        return []
