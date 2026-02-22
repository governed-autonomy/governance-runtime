from __future__ import annotations

import json
import subprocess
import sys


def test_cli_action_derives_effects_login(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"always_human_domains": ["google.com"]}), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "governance_runtime",
        "decide",
        "--url",
        "https://mail.google.com/",
        "--action",
        "login",
        "--profile",
        "standard",
        "--config",
        str(cfg_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["decision"] == "DENY"


def test_cli_action_derives_effects_send_message(tmp_path):
    cmd = [
        sys.executable,
        "-m",
        "governance_runtime",
        "decide",
        "--action",
        "send-message",
        "--request",
        "Send a message to Alex",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["decision"] == "ASK"
