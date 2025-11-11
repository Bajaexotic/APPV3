import importlib.util
import os
import pathlib
import socket

import pytest


def _load_probe():
    root = pathlib.Path(__file__).resolve().parents[1]
    probe_path = root / "tools" / "dtc_probe.py"
    spec = importlib.util.spec_from_file_location("dtc_probe", probe_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(
    os.getenv("RUN_DTC_E2E", "0") != "1",
    reason="Set RUN_DTC_E2E=1 to run against a live Sierra Chart DTC server",
)
def test_dtc_probe_end_to_end():
    host = os.getenv("DTC_HOST", "127.0.0.1")
    port = int(os.getenv("DTC_PORT", "11099"))
    # Fast pre-check to skip if no listener
    try:
        with socket.create_connection((host, port), timeout=1):
            pass
    except Exception as e:
        pytest.skip(f"No DTC listener at {host}:{port} ({e})")

    probe = _load_probe()
    rc = probe.main()
    assert rc == 0
