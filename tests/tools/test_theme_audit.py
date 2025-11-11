from __future__ import annotations

from tools.theme_audit import audit


def test_theme_audit_basic():
    report = audit()
    assert "keys" in report
    keys = report["keys"]
    assert isinstance(keys.get("debug"), list)
    assert isinstance(keys.get("sim"), list)
    assert isinstance(keys.get("live"), list)
    # missing_in_schema may be empty but must exist
    assert "missing_in_schema" in keys
    assert isinstance(keys["missing_in_schema"], list)
    # invalid_colors is a dict
    assert isinstance(report.get("invalid_colors"), dict)
