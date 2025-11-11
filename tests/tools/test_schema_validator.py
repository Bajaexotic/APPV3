from __future__ import annotations

from tools.schema_validator import validate_against_spec


def test_schema_validator_with_minimal_spec():
    # Minimal spec: only a small subset of fields that certainly exist
    spec = {
        "301": {"fields": ["ServerOrderID", "Symbol"]},
        "306": {"fields": ["Symbol", "Quantity"]},
        "304": {"fields": ["Symbol"]},
        "401": {"fields": ["TradeAccount"]},
        "600": {"fields": ["TradeAccount", "CashBalance"]},
    }
    results = validate_against_spec(spec)
    # Ensure keys present and models recognized
    for k in ("301", "306", "304", "401", "600"):
        assert k in results
        r = results[k]
        assert "model" in r and "missing" in r and "extra" in r and "ok" in r
        # Should be OK because requested fields exist in models
        assert r["ok"] is True
