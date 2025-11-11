# -------------------- test_theme_consistency (start)
import re

from config import theme


HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")
OKLCH_RE = re.compile(r"^oklch\(\s*[\d.]+%?\s+[\d.]+\s+[\d.]+\s*\)$")


def _is_color(value: str) -> bool:
    """Detect if a value looks like a color (hex or oklch)."""
    if not isinstance(value, str):
        return False
    return bool(HEX_RE.match(value) or OKLCH_RE.match(value) or value.startswith("rgb"))


def test_all_themes_have_same_keys():
    """Ensure DEBUG, LIVE, and SIM themes contain identical keys."""
    base_keys = set(theme.DEBUG_THEME.keys())
    for name, t in [("LIVE", theme.LIVE_THEME), ("SIM", theme.SIM_THEME)]:
        missing = base_keys - set(t.keys())
        extra = set(t.keys()) - base_keys
        assert not missing, f"{name} missing keys: {missing}"
        assert not extra, f"{name} has extra keys: {extra}"


def test_all_modes_cover_base_theme():
    """Ensure every mode defines all keys from _BASE_THEME."""
    base_keys = set(theme._BASE_THEME.keys())
    for name, t in [
        ("DEBUG", theme.DEBUG_THEME),
        ("LIVE", theme.LIVE_THEME),
        ("SIM", theme.SIM_THEME),
    ]:
        missing = base_keys - set(t.keys())
        assert not missing, f"{name} missing base keys: {missing}"


def test_color_fields_are_valid_formats():
    """Ensure all color-like fields are valid hex or OKLCH strings."""
    for name, t in [
        ("DEBUG", theme.DEBUG_THEME),
        ("LIVE", theme.LIVE_THEME),
        ("SIM", theme.SIM_THEME),
    ]:
        bad_colors = {}
        for k, v in t.items():
            if isinstance(v, str) and (
                "color" in k or "bg" in k or "fg" in k or "ink" in k or "accent" in k or "border" in k or "pnl" in k
            ):
                if not _is_color(v) and v not in ("none", "transparent"):
                    bad_colors[k] = v
        assert not bad_colors, f"{name} theme has invalid color values: {bad_colors}"


def test_theme_types_match_debug_baseline():
    """Ensure LIVE and SIM theme values match DEBUG types."""
    baseline = {k: type(v) for k, v in theme.DEBUG_THEME.items()}
    for name, t in [("LIVE", theme.LIVE_THEME), ("SIM", theme.SIM_THEME)]:
        mismatched = {k: (type(t[k]), baseline[k]) for k in t if k in baseline and type(t[k]) is not baseline[k]}
        assert not mismatched, f"{name} theme type mismatches: {mismatched}"


# -------------------- test_theme_consistency (end)
