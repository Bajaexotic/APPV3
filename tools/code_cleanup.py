from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import sys
from typing import Dict, List, Set


try:
    from tools._common import DEFAULT_REPORTS, add_common_args, write_json
except Exception:
    from _common import DEFAULT_REPORTS, add_common_args, write_json

__scope__ = "maintenance.code_cleanup"


# ============================================================================
# Intra-File Analysis (Dead Code Finder)
# ============================================================================


class UsageVisitor(ast.NodeVisitor):
    """AST visitor to collect all referenced names in a file."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        self.names.add(node.id)
        self.generic_visit(node)


def analyze_file(path: Path) -> dict[str, list[str]]:
    """
    Analyze a single file for unused imports, functions, and classes.

    Args:
        path: Path to Python file

    Returns:
        Dict with unused_functions, unused_classes, unused_imports lists
    """
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return {"unused_functions": [], "unused_classes": [], "unused_imports": []}

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return {"unused_functions": [], "unused_classes": [], "unused_imports": []}

    defined_funcs: set[str] = set()
    defined_classes: set[str] = set()
    imports: set[str] = set()

    # Collect definitions
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defined_funcs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            defined_classes.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.asname or n.name.split(".")[0])
            else:
                for n in node.names:
                    imports.add(n.asname or n.name)

    # Collect usage
    usage = UsageVisitor()
    usage.visit(tree)

    # Find unused (excluding private names with leading underscore)
    unused_funcs = sorted([n for n in defined_funcs if n not in usage.names and not n.startswith("_")])
    unused_classes = sorted([n for n in defined_classes if n not in usage.names and not n.startswith("_")])
    unused_imports = sorted([n for n in imports if n not in usage.names])

    return {
        "unused_functions": unused_funcs,
        "unused_classes": unused_classes,
        "unused_imports": unused_imports,
    }


def find_dead_code_in_files(paths: list[str], repo: Path) -> dict[str, dict[str, list[str]]]:
    """
    Find dead code in specified directories.

    Args:
        paths: List of relative directory paths to scan
        repo: Repository root path

    Returns:
        Dict mapping file path to unused code report
    """
    report: dict[str, dict[str, list[str]]] = {}

    for rel in paths:
        root = repo / rel
        if not root.exists():
            continue

        for dirpath, _, files in os.walk(root):
            if any(p in dirpath for p in (".venv", "__pycache__")):
                continue

            for f in files:
                if f.endswith(".py"):
                    p = Path(dirpath) / f
                    res = analyze_file(p)
                    if any(res.values()):
                        report[str(p)] = res

    return report


# ============================================================================
# Inter-File Analysis (Module Cleanup)
# ============================================================================


def collect_imports(root: Path) -> set[str]:
    """
    Collect all imported module names from Python files.

    Args:
        root: Repository root path

    Returns:
        Set of imported module names
    """
    imported: set[str] = set()

    for dirpath, _, files in os.walk(root):
        if any(p in dirpath for p in (".venv", "__pycache__", "tests", "tools")):
            continue

        for f in files:
            if not f.endswith(".py"):
                continue

            p = Path(dirpath) / f
            try:
                src = p.read_text(encoding="utf-8")
            except Exception:
                continue

            try:
                tree = ast.parse(src, filename=str(p))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imported.add(n.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module.split(".")[0])

    return imported


def list_modules(root: Path) -> dict[str, str]:
    """
    List all Python modules (files) in the repository.

    Args:
        root: Repository root path

    Returns:
        Dict mapping module name to file path
    """
    modules: dict[str, str] = {}

    for dirpath, _, files in os.walk(root):
        if any(p in dirpath for p in (".venv", "__pycache__", "tests", "tools")):
            continue

        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                p = Path(dirpath) / f
                modules[p.stem] = str(p)

    return modules


def find_unused_modules(repo: Path) -> dict[str, str]:
    """
    Find Python modules that are never imported.

    Args:
        repo: Repository root path

    Returns:
        Dict mapping unused module name to file path
    """
    imported = collect_imports(repo)
    modules = list_modules(repo)
    unused = {name: path for name, path in modules.items() if name not in imported}

    return unused


# ============================================================================
# Main CLI
# ============================================================================


def main(argv: list[str]) -> int:
    """
    Main entry point for code cleanup tool.

    Combines functionality of dead_code_finder.py and module_cleanup.py.
    """
    ap = argparse.ArgumentParser(description="Find unused code at file and module level")
    ap.add_argument(
        "--level",
        choices=["file", "module", "all"],
        default="all",
        help="Analysis level: file (intra-file), module (inter-file), or all",
    )
    ap.add_argument(
        "--paths",
        nargs="+",
        default=["core", "services", "panels", "widgets", "utils", "config"],
        help="Directories to scan for file-level analysis",
    )
    add_common_args(ap)
    ap.set_defaults(out=str(DEFAULT_REPORTS / "code_cleanup.json"))
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    report: dict[str, any] = {}

    # File-level analysis (dead code within files)
    if args.level in ("file", "all"):
        print("🔍 Scanning for unused code in files...")
        file_report = find_dead_code_in_files(args.paths, repo)
        report["file_level"] = file_report

        total_files = len(file_report)
        total_unused = sum(
            len(r["unused_functions"]) + len(r["unused_classes"]) + len(r["unused_imports"])
            for r in file_report.values()
        )
        print(f"   Found {total_unused} unused items across {total_files} files")

    # Module-level analysis (unused modules)
    if args.level in ("module", "all"):
        print("🔍 Scanning for unused modules...")
        module_report = find_unused_modules(repo)
        report["module_level"] = module_report
        print(f"   Found {len(module_report)} unused modules")

    # Write report
    out_path = Path(args.out)
    write_json(report, out_path)

    if not args.quiet:
        print(f"\n✅ Code cleanup report written to {out_path}")
        if args.level in ("file", "all") and report.get("file_level"):
            print(f"   File-level: {len(report['file_level'])} files with unused code")
        if args.level in ("module", "all") and report.get("module_level"):
            print(f"   Module-level: {len(report['module_level'])} unused modules")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
