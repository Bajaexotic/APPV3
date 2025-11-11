from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys
from typing import Any, Dict


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, parse_kv_file, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, parse_kv_file, write_json

__scope__ = "validation.config_integrity"


def extract_settings_vars(settings_path: Path) -> dict[str, Any]:
    data = settings_path.read_text(encoding="utf-8")
    tree = ast.parse(data, filename=str(settings_path))
    out: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        value = None
                    out[target.id] = value
    return out


def guess_type(s: str) -> Any:
    if s.lower() in {"true", "false"}:
        return s.lower() == "true"
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        return s


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Check .env and config/settings.py for missing or mismatched keys")
    ap.add_argument("--env", default=".env", help="Path to .env file")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "config_integrity.json"))
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    settings_path = repo_root / "config" / "settings.py"
    env_path = repo_root / args.env

    env_kv = parse_kv_file(env_path)
    settings_vars = extract_settings_vars(settings_path)

    missing_env = [k for k in settings_vars.keys() if k not in env_kv]
    mismatched: dict[str, Any] = {}
    for k, v in settings_vars.items():
        if k in env_kv:
            ev = guess_type(env_kv[k])
            if type(ev) != type(v):
                mismatched[k] = {"expected_type": type(v).__name__, "env_type": type(ev).__name__}

    report = {
        "env_path": str(env_path),
        "missing_env": missing_env,
        "mismatched_types": mismatched,
        "settings_var_count": len(settings_vars),
    }
    out_path = Path(args.out)
    write_json(report, out_path)
    if not args.quiet:
        print(f"Config integrity report written to {out_path}")
        if missing_env:
            print(f"Missing env keys: {len(missing_env)}")
        if mismatched:
            print(f"Type mismatches: {len(mismatched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
