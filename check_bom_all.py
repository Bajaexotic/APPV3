#!/usr/bin/env python3
"""
Check ALL files for BOM markers (not just Python files).
"""

from pathlib import Path


def check_file_for_bom(file_path: Path) -> tuple[bool, str]:
    """
    Check if a file has BOM markers.

    Returns (has_bom, bom_type)
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)

        if len(header) >= 3 and header[:3] == b"\xef\xbb\xbf":
            return True, "UTF-8 BOM"
        elif len(header) >= 2 and header[:2] == b"\xff\xfe":
            return True, "UTF-16 LE BOM"
        elif len(header) >= 2 and header[:2] == b"\xfe\xff":
            return True, "UTF-16 BE BOM"
        elif len(header) >= 4 and header[:4] == b"\xff\xfe\x00\x00":
            return True, "UTF-32 LE BOM"
        elif len(header) >= 4 and header[:4] == b"\x00\x00\xfe\xff":
            return True, "UTF-32 BE BOM"

        return False, ""

    except Exception:
        return False, ""


def main():
    """Check all text files for BOM."""
    project_root = Path(__file__).parent

    # Extensions to check
    text_extensions = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".rst", ".cfg", ".ini"}

    # Directories to scan
    directories_to_scan = [
        ".",  # Root
        "config",
        "core",
        "panels",
        "services",
        "ui",
        "utils",
        "widgets",
        "docs",
        "tests",
    ]

    print("=" * 70)
    print("Checking ALL files for BOM markers")
    print("=" * 70)
    print()

    files_with_bom = []

    for directory in directories_to_scan:
        dir_path = project_root / directory
        if not dir_path.exists():
            continue

        # Check all text files
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if it's a text file we care about
            if file_path.suffix in text_extensions or file_path.name in ["README", "LICENSE", "CHANGELOG"]:
                has_bom, bom_type = check_file_for_bom(file_path)
                if has_bom:
                    relative_path = file_path.relative_to(project_root)
                    files_with_bom.append((relative_path, bom_type))
                    print(f"⚠️  {bom_type}: {relative_path}")

    print()
    print("=" * 70)

    if files_with_bom:
        print(f"❌ Found {len(files_with_bom)} file(s) with BOM markers")
        print()
        print("These files need to be fixed!")
    else:
        print("✅ No files with BOM markers found")
        print()
        print("All files are clean UTF-8 without BOM")

    print("=" * 70)


if __name__ == "__main__":
    main()
