from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "reporting.changelog_builder"


def git_log(since: str | None) -> str:
    args = ["git", "log", "--pretty=%H%x09%s"]
    if since:
        args.insert(2, f"{since}..HEAD")
    try:
        out = subprocess.check_output(args, text=True)
        return out
    except Exception as e:
        return ""


def categorize(lines: list[str]) -> dict:
    sections = {"feat": [], "fix": [], "refactor": [], "docs": [], "chore": [], "other": []}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        msg = parts[1] if len(parts) > 1 else parts[0]
        lower = msg.lower()
        placed = False
        for k in ("feat", "fix", "refactor", "docs", "chore"):
            if lower.startswith(k + ":"):
                sections[k].append(msg)
                placed = True
                break
        if not placed:
            sections["other"].append(msg)
    return sections


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build a CHANGELOG section from git history (Conventional Commits)")
    ap.add_argument("--since", help="Git ref/tag to start from (e.g., v1.2.0)")
    ap.add_argument("--write", help="Write to CHANGELOG.md (path)")
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "changelog.json"))
    args = ap.parse_args(argv)

    log = git_log(args.since)
    lines = log.splitlines()
    sections = categorize(lines)

    out_path = Path(args.out)
    write_json(sections, out_path)
    print(f"Changelog JSON written to {out_path}")

    if args.write:
        md = ["## Changes\n"]
        for k in ("feat", "fix", "refactor", "docs", "chore", "other"):
            if sections[k]:
                md.append(f"### {k}\n")
                md += [f"- {m}\n" for m in sections[k]]
        Path(args.write).write_text("".join(md), encoding="utf-8")
        print(f"CHANGELOG written to {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
