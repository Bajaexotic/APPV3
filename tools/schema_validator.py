from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "validation.schema_validator"


def load_local_spec(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against_spec(spec: dict[str, Any]) -> dict[str, Any]:
    from services.dtc_schemas import DTC_MESSAGE_REGISTRY

    results: dict[str, Any] = {}
    for msg_type, model in DTC_MESSAGE_REGISTRY.items():
        expected = set(map(str, spec.get(str(msg_type), {}).get("fields", [])))
        actual = set(getattr(model, "model_fields", model.__fields__).keys())
        missing = sorted(list(expected - actual))
        extra = sorted(list(actual - expected))
        results[str(msg_type)] = {
            "model": model.__name__,
            "missing": missing,
            "extra": extra,
            # Treat spec as a minimum contract: extras are allowed, missing is not.
            "ok": not missing,
        }
    return results


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate local DTC schemas against a JSON spec")
    ap.add_argument("--spec", required=True, help="Path to local DTC spec JSON (no network)")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "dtc_schema_validation.json"))
    args = ap.parse_args(argv)

    spec = load_local_spec(Path(args.spec))
    results = validate_against_spec(spec)

    out_path = Path(args.out)
    write_json(results, out_path)
    if not args.quiet:
        total = len(results)
        ok = sum(1 for r in results.values() if r["ok"])
        print(f"Schema validation: {ok}/{total} types matched. Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
