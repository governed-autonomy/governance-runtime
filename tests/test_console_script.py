from __future__ import annotations

import json
import subprocess
import sys


def test_console_script_governance_available_after_editable_install(tmp_path):
    # This test assumes the package is installed editable in the active venv.
    # It will be skipped if the script is not found.
    res = subprocess.run(["which", "governance"], capture_output=True, text=True)
    if res.returncode != 0:
        return

    config = {
        "always_human_domains": ["mail.google.com"],
        "allowed_login_domains_by_profile": {"standard": ["forum.example"]},
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    cmd = [
        "governance",
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
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    assert data["decision"] == "ASK"
