from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Dict


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "maintenance.theme_refactor"


def build_plan(renames: dict[str, str]) -> dict[str, dict]:
    repo = Path(__file__).resolve().parents[1]
    plan: dict[str, dict] = {}
    pattern = re.compile(r"THEME\[[\'\"]([A-Za-z0-9_]+)[\'\"]\]")
    for root, _, files in os.walk(repo):
        if any(part in {".venv", ".git", "__pycache__", "logs", "reports"} for part in Path(root).parts):
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            p = Path(root) / f
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            hits = []
            for m in pattern.finditer(text):
                k = m.group(1)
                if k in renames:
                    hits.append({"old": k, "new": renames[k], "pos": m.start()})
            if hits:
                plan[str(p)] = {"count": len(hits), "changes": hits}
    return plan


def apply_plan(plan: dict[str, dict]) -> int:
    changed = 0
    for file, info in plan.items():
        p = Path(file)
        text = p.read_text(encoding="utf-8")
        for ch in info.get("changes", []):
            text = re.sub(rf"THEME\[['\"]{re.escape(ch['old'])}['\"]\]", f"THEME['{ch['new']}']", text)
        p.write_text(text, encoding="utf-8")
        changed += 1
    return changed


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Safely refactor/rename theme keys across the repo")
    ap.add_argument("--rename", nargs="+", help="Pairs old=new")
    ap.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "theme_refactor_plan.json"))
    args = ap.parse_args(argv)

    renames: dict[str, str] = {}
    for pair in args.rename or []:
        if "=" in pair:
            old, new = pair.split("=", 1)
            renames[old] = new

    plan = build_plan(renames)
    out_path = Path(args.out)
    write_json(plan, out_path)
    if args.apply:
        changed = apply_plan(plan)
        print(f"Applied changes to {changed} files. Plan saved: {out_path}")
    else:
        print(f"Dry-run. Plan saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
