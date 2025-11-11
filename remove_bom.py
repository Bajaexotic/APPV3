#!/usr/bin/env python3
"""
Remove UTF-8 BOM (Byte Order Mark) from all Python files in the project.

The BOM (0xEF 0xBB 0xBF) causes issues with Poetry installation.
"""

import os
from pathlib import Path


def remove_bom_from_file(file_path: Path) -> bool:
    """
    Remove BOM from a file if present.

    Returns True if BOM was removed, False otherwise.
    """
    try:
        # Read file as bytes
        with open(file_path, "rb") as f:
            content = f.read()

        # Check for UTF-8 BOM (EF BB BF)
        if content.startswith(b"\xef\xbb\xbf"):
            # Remove BOM
            content = content[3:]

            # Write back without BOM
            with open(file_path, "wb") as f:
                f.write(content)

            print(f"✓ Removed BOM from: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    """Remove BOM from all Python files in the project."""
    project_root = Path(__file__).parent

    # Directories to scan
    directories = ["config", "core", "panels", "services", "ui", "utils", "widgets"]

    total_fixed = 0
    total_scanned = 0

    print("=" * 60)
    print("Removing UTF-8 BOM from Python files")
    print("=" * 60)
    print()

    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            continue

        # Find all Python files
        for py_file in dir_path.rglob("*.py"):
            total_scanned += 1
            if remove_bom_from_file(py_file):
                total_fixed += 1

    print()
    print("=" * 60)
    print(f"Summary: Fixed {total_fixed} files out of {total_scanned} scanned")
    print("=" * 60)


if __name__ == "__main__":
    main()
