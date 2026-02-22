from __future__ import annotations

import json
import subprocess
import sys


def test_cli_config_commands_minimal(tmp_path):
    cfg = {
        "always_human_domains": [],
        "allowed_login_domains_by_profile": {"standard": []},
        "override_always_human_domains_by_profile": {"standard": []},
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    # allow-login
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "allow-login",
            "--profile",
            "standard",
            "--domain",
            "forum.example",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # always-human
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
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

    # override-always-human
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "override-always-human",
            "--profile",
            "standard",
            "--domain",
            "google.com",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # Now decide on a google login (standard) should be ASK (because override + allow-login)
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "decide",
            "--url",
            "https://mail.google.com/",
            "--effects",
            "LOGIN",
            "CREDENTIALS",
            "--profile",
            "standard",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(out.stdout)
    assert data["decision"] == "DENY"  # still deny because not allowlisted for google.com

    # Allow login for google.com and retry -> ASK
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "allow-login",
            "--profile",
            "standard",
            "--domain",
            "google.com",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    out2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "decide",
            "--url",
            "https://mail.google.com/",
            "--effects",
            "LOGIN",
            "CREDENTIALS",
            "--profile",
            "standard",
            "--config",
            str(cfg_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data2 = json.loads(out2.stdout)
    assert data2["decision"] == "ASK"
