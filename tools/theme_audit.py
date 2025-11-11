from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, Set


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
    from tools.theme_validation import is_color_like_key, is_color_token
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json
    from theme_validation import is_color_like_key, is_color_token

__scope__ = "validation.theme_audit"


def audit() -> dict[str, Any]:
    # Import theme modules
    from config import theme as theme_mod

    try:
        from config.theme_schema import ThemeSchema  # type: ignore

        schema_keys: set[str] = set(getattr(ThemeSchema, "model_fields", ThemeSchema.__fields__).keys())
    except Exception:
        schema_keys = set()

    live_theme: dict[str, Any] = dict(theme_mod.THEME)
    debug_theme: dict[str, Any] = dict(theme_mod.DEBUG_THEME)
    sim_theme: dict[str, Any] = dict(theme_mod.SIM_THEME)
    live_theme_keys = set(live_theme.keys())

    # Key consistency
    debug_keys = set(debug_theme.keys())
    sim_keys = set(sim_theme.keys())
    all_keys = debug_keys | sim_keys | live_theme_keys
    in_schema_only = schema_keys - all_keys
    missing_in_schema = all_keys - schema_keys if schema_keys else set()

    # Color validation (using shared utility)
    invalid_colors: dict[str, Any] = {}
    for k, v in debug_theme.items():
        if is_color_like_key(k) and isinstance(v, str) and not is_color_token(v):
            invalid_colors[k] = v

    # Code references of THEME[...] keys
    code_refs: dict[str, int] = {}
    repo_root = Path(__file__).resolve().parents[1]
    for root, _, files in os.walk(repo_root):
        if any(part in {".venv", "__pycache__", ".git", "logs", "reports"} for part in Path(root).parts):
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            p = Path(root) / f
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for m in re.finditer(r"THEME\[[\'\"]([A-Za-z0-9_]+)[\'\"]\]", text):
                key = m.group(1)
                code_refs[key] = code_refs.get(key, 0) + 1

    return {
        "keys": {
            "debug": sorted(list(debug_keys)),
            "sim": sorted(list(sim_keys)),
            "live": sorted(list(live_theme_keys)),
            "schema": sorted(list(schema_keys)),
            "missing_in_schema": sorted(list(missing_in_schema)),
            "schema_only": sorted(list(in_schema_only)),
        },
        "invalid_colors": invalid_colors,
        "code_refs_count": code_refs,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Audit theme keys and color tokens")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "theme_audit.json"))
    args = ap.parse_args(argv)

    report = audit()
    out_path = Path(args.out)
    write_json(report, out_path)

    if not args.quiet:
        missing = report["keys"]["missing_in_schema"]
        invalid = report["invalid_colors"]
        print(f"Theme audit written to {out_path}")
        if missing:
            print(f"Missing in schema: {len(missing)}")
        if invalid:
            print(f"Invalid colors: {len(invalid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
