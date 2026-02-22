from __future__ import annotations

import json
import subprocess
import sys


def test_cli_config_show_prints_path_and_json(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"always_human_domains": ["google.com"]}), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "governance_runtime",
        "config-show",
        "--config",
        str(cfg_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Config:" in res.stdout
    assert "google.com" in res.stdout
