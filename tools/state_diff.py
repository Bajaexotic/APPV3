from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import importlib
import json
from pathlib import Path
import sys
from typing import Any


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "diagnostics.state_diff"


def to_basic(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: to_basic(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_basic(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def import_symbol(target: str) -> Any:
    mod_name, sym_name = target.split(":", 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, sym_name)


def snapshot(target: str) -> Any:
    sym = import_symbol(target)
    try:
        inst = sym() if callable(sym) else sym
    except Exception:
        inst = sym
    data = getattr(inst, "__dict__", inst)
    return to_basic(data)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Capture and diff object state before/after an action")
    ap.add_argument("--target", required=True, help="Import path to symbol (module:Name)")
    ap.add_argument("--action", default=None, help="Optional action to import and run (module:callable)")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "state_diff.json"))
    args = ap.parse_args(argv)

    before = snapshot(args.target)
    if args.action:
        act = import_symbol(args.action)
        try:
            act()
        except Exception:
            pass
    after = snapshot(args.target)

    diff = {"before": before, "after": after}
    out_path = Path(args.out)
    write_json(diff, out_path)
    print(f"State diff written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
