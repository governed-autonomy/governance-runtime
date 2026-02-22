from __future__ import annotations

import json
import subprocess
import sys


def test_cli_explain_outputs_human_text(tmp_path):
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
        "--pretty",
        "--explain",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Decision:" in res.stdout


def test_cli_config_remove(tmp_path):
    cfg = {
        "always_human_domains": ["google.com"],
        "allowed_login_domains_by_profile": {"standard": ["forum.example"]},
        "override_always_human_domains_by_profile": {"standard": ["google.com"]},
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    # remove always-human domain
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "config-remove",
            "--field",
            "always-human",
            "--domain",
            "google.com",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    new_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "google.com" not in new_cfg["always_human_domains"]
