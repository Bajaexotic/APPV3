# -------------------- test_theme_drift (start)
from config import theme
from config.theme_schema import ThemeSchema


def test_theme_schema_drift():
    """
    Ensures the ThemeSchema (formal schema) matches the live DEBUG_THEME keys.
    Fails if you add/remove keys in config/theme.py but forget to update the schema.
    """
    base_keys = set(theme.DEBUG_THEME.keys())
    # Pydantic v2: use model_fields instead of deprecated __fields__
    schema_keys = set(ThemeSchema.model_fields.keys())

    missing_in_schema = base_keys - schema_keys
    extra_in_schema = schema_keys - base_keys

    assert not missing_in_schema, f"Schema missing keys: {missing_in_schema}"
    assert not extra_in_schema, f"Schema has extra keys: {extra_in_schema}"


# -------------------- test_theme_drift (end)
