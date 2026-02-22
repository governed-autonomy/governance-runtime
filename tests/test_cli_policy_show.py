from __future__ import annotations

import json
import subprocess
import sys


def test_policy_show_prints_table(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        json.dumps({"action_policies_by_profile": {"experimental": {"purchase": "ALLOW"}}}),
        encoding="utf-8",
    )
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "policy-show",
            "--profile",
            "experimental",
            "--config",
            str(cfg_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Profile: experimental" in res.stdout
    assert "purchase: ALLOW" in res.stdout
