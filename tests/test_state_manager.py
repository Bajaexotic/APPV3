# File: tests/test_state_manager.py
# Block 30/?? Ã¢â‚¬â€ Unit tests for StateManager
import pytest

from core.state_manager import StateManager


def test_set_and_get_value():
    s = StateManager()
    s.set("x", 123)
    assert s.get("x") == 123


def test_default_value():
    s = StateManager()
    assert s.get("missing", 42) == 42


def test_delete_key():
    s = StateManager()
    s.set("a", 1)
    s.delete("a")
    assert s.get("a") is None


def test_clear_state():
    s = StateManager()
    s.set("a", 1)
    s.set("b", 2)
    s.clear()
    assert len(s.dump()) == 0


def test_positions_roundtrip():
    s = StateManager()
    sample_positions = [{"symbol": "MESZ25", "qty": 1, "avg": 5050.0}]
    s.set_positions(sample_positions)
    assert s.get_positions() == sample_positions


def test_keys_list():
    s = StateManager()
    s.set("x", 5)
    s.set("y", 10)
    keys = s.keys()
    assert "x" in keys and "y" in keys
