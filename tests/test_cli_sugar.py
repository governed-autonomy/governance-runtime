from __future__ import annotations

import json
import subprocess
import sys


def test_cli_sugar_url_effects_profile(tmp_path):
    config = {
        "always_human_domains": ["mail.google.com"],
        "allowed_login_domains_by_profile": {"standard": ["forum.example"]},
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "governance_runtime",
        "decide",
        "--url",
        "forum.example/login",
        "--effects",
        "LOGIN",
        "CREDENTIALS",
        "--profile",
        "standard",
        "--config",
        str(cfg_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["decision"] == "ASK"
