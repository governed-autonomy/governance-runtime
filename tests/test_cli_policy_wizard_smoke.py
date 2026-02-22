from __future__ import annotations

import json
import subprocess
import sys


def test_policy_wizard_writes_config(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"action_policies_by_profile": {}}), encoding="utf-8")

    # Feed: profile, action, decision, then done
    inp = "experimental\npurchase\nASK\n(done)\n"
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "policy-wizard",
            "--config",
            str(cfg_path),
        ],
        input=inp,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "OK: action_policies_by_profile" in res.stdout
    new_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert new_cfg["action_policies_by_profile"]["experimental"]["purchase"] == "ASK"
