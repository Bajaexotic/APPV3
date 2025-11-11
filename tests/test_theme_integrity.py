# -------------------- test_theme_integrity (start)
from pydantic import ValidationError

from config import theme
from config.theme_schema import ThemeSchema


def validate_theme(name: str, theme_dict: dict):
    """Helper that validates a theme dict against ThemeSchema."""
    try:
        ThemeSchema(**theme_dict)
    except ValidationError as e:
        raise AssertionError(f"{name} theme validation failed:\n{e}")


def test_debug_theme_integrity():
    """Ensure DEBUG_THEME passes schema validation."""
    validate_theme("DEBUG", theme.DEBUG_THEME)


def test_sim_theme_integrity():
    """Ensure SIM_THEME passes schema validation."""
    validate_theme("SIM", theme.SIM_THEME)


def test_live_theme_integrity():
    """Ensure LIVE_THEME passes schema validation."""
    validate_theme("LIVE", theme.LIVE_THEME)


# -------------------- test_theme_integrity (end)
