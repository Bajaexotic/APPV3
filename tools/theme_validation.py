"""
Theme Validation Shared Utilities
----------------------------------
Extracted shared validation logic from sync_theme_schema.py and theme_audit.py
to eliminate duplication and provide consistent theme validation across tools.

Usage:
    from tools.theme_validation import (
        validate_theme_keys,
        is_color_token,
        infer_type
    )
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, Set


__scope__ = "validation.theme_validation"


# ============================================================================
# Type Inference
# ============================================================================


def infer_type(value: Any) -> str:
    """
    Infer Python type name from value.

    Args:
        value: Any Python value

    Returns:
        Type name as string (bool/int/float/str)
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


# ============================================================================
# Color Validation
# ============================================================================


HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")
OKLCH_RE = re.compile(r"^oklch\(\s*[\d.]+%?\s+[\d.]+\s+[\d.]+\s*\)$")


def is_color_token(s: str) -> bool:
    """
    Check if string is a valid color token (hex or oklch).

    Supports:
        - Hex: #RRGGBB
        - OKLCH: oklch(L C H)
        - RGB/RGBA: rgb(...) rgba(...)

    Args:
        s: String to validate

    Returns:
        True if valid color token
    """
    if not isinstance(s, str):
        return False

    # Allow special values
    if s.lower() in ("none", "transparent"):
        return True

    # Hex color
    if HEX_RE.match(s):
        return True

    # OKLCH color
    if OKLCH_RE.match(s):
        return True

    # RGB/RGBA color
    if s.lower().startswith(("rgb(", "rgba(", "oklch(")):
        return True

    return False


def is_color_like_key(key: str) -> bool:
    """
    Check if key name suggests it should contain a color value.

    Args:
        key: Theme key name

    Returns:
        True if key appears to be color-related
    """
    color_indicators = [
        "color",
        "bg",
        "fg",
        "ink",
        "text",
        "border",
        "badge",
        "pnl",
        "glow",
        "primary",
        "secondary",
        "muted",
        "dim",
        "elevated",
        "panel",
        "card",
    ]

    key_lower = key.lower()
    return any(indicator in key_lower for indicator in color_indicators)


# ============================================================================
# Theme Validation
# ============================================================================


def validate_theme_keys(themes: dict[str, dict[str, Any]]) -> dict:
    """
    Validate consistency across multiple theme dictionaries.

    Checks:
        - Key consistency (all themes have same keys)
        - Type consistency (same key has same type across themes)
        - Color token validity (color-related keys have valid color values)

    Args:
        themes: Dict mapping theme name to theme dictionary
                e.g., {"DEBUG_THEME": {...}, "SIM_THEME": {...}}

    Returns:
        Validation report dict with structure:
        {
            "timestamp": ISO timestamp,
            "themes": {
                "theme_name": {
                    "missing_keys": [list of missing keys],
                    "extra_keys": [list of extra keys],
                    "type_mismatches": {key: {"expected": type, "found": type}},
                    "invalid_colors": {key: value}
                }
            },
            "summary": "status message"
        }
    """
    if not themes:
        return {"error": "No themes provided"}

    # Get reference theme (first one)
    base_name = next(iter(themes))
    base_keys = set(themes[base_name].keys())

    report = {"timestamp": datetime.now().isoformat(), "themes": {}, "summary": ""}

    consistent = True

    # Check key consistency
    for name, theme in themes.items():
        theme_keys = set(theme.keys())
        missing = sorted(base_keys - theme_keys)
        extra = sorted(theme_keys - base_keys)

        report["themes"][name] = {
            "missing_keys": missing,
            "extra_keys": extra,
            "type_mismatches": {},
            "invalid_colors": {},
        }

        if missing or extra:
            consistent = False

    # Check type consistency
    ref_types = {k: type(v).__name__ for k, v in themes[base_name].items()}

    for name, theme in themes.items():
        type_mismatches = {}
        for key, value in theme.items():
            if key in ref_types and type(value).__name__ != ref_types[key]:
                type_mismatches[key] = {"expected": ref_types[key], "found": type(value).__name__}

        if type_mismatches:
            consistent = False
            report["themes"][name]["type_mismatches"] = type_mismatches

    # Check color validity
    for name, theme in themes.items():
        invalid_colors = {}
        for key, value in theme.items():
            if is_color_like_key(key) and isinstance(value, str):
                if not is_color_token(value):
                    invalid_colors[key] = value

        if invalid_colors:
            consistent = False
            report["themes"][name]["invalid_colors"] = invalid_colors

    report["summary"] = "All themes consistent" if consistent else "One or more inconsistencies found"

    return report


def extract_theme_keys(theme_dict: dict[str, Any]) -> set[str]:
    """
    Extract all keys from a theme dictionary.

    Args:
        theme_dict: Theme dictionary

    Returns:
        Set of theme keys
    """
    return set(theme_dict.keys())


def compare_theme_to_schema(theme_dict: dict[str, Any], schema_keys: set[str]) -> dict[str, list]:
    """
    Compare theme dictionary keys against schema keys.

    Args:
        theme_dict: Theme dictionary to validate
        schema_keys: Set of keys defined in schema

    Returns:
        Dict with:
            - "missing_in_schema": keys in theme but not schema
            - "missing_in_theme": keys in schema but not theme
    """
    theme_keys = set(theme_dict.keys())

    return {"missing_in_schema": sorted(theme_keys - schema_keys), "missing_in_theme": sorted(schema_keys - theme_keys)}


# ============================================================================
# Module Test
# ============================================================================


if __name__ == "__main__":
    # Quick validation test
    test_themes = {
        "THEME_A": {"bg_primary": "#1a1a1a", "fg_primary": "#ffffff", "font_size": 12, "enabled": True},
        "THEME_B": {"bg_primary": "#2a2a2a", "fg_primary": "#eeeeee", "font_size": 14, "enabled": False},
    }

    report = validate_theme_keys(test_themes)
    print(f"Validation: {report['summary']}")

    # Test color validation
    assert is_color_token("#1a1a1a") == True
    assert is_color_token("oklch(50% 0.5 180)") == True
    assert is_color_token("invalid") == False
    assert is_color_token("transparent") == True

    print("All validation tests passed!")
