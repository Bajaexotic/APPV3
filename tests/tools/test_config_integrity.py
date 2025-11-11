from __future__ import annotations

from pathlib import Path
import tempfile

from tools.config_integrity import main as config_integrity_main


def test_config_integrity_generates_report(tmp_path: Path):
    # Create a temporary .env file (may not cover all settings, which is fine)
    env_path = tmp_path / ".env"
    env_path.write_text("SAMPLE_KEY=1\n", encoding="utf-8")
    out_path = tmp_path / "config_integrity.json"

    rc = config_integrity_main(["--env", str(env_path), "--out", str(out_path), "--quiet"])  # type: ignore[arg-type]
    assert rc == 0
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "missing_env" in content
