from __future__ import annotations

# File: core/__init__.py
# Package export surface for core
# Re-export key classes/helpers for convenient imports
from .app_manager import MainWindow
from .data_bridge import DTCClientJSON
from .persistence import (
    append_cache,
    append_jsonl,
    ensure_cache_dir,
    read_cache_between,
    read_jsonl,
)
