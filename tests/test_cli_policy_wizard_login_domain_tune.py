from __future__ import annotations

import json
import subprocess
import sys


def test_policy_wizard_login_domain_tune_yes_adds_allowlist(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        json.dumps(
            {
                "action_policies_by_profile": {},
                "allowed_login_domains_by_profile": {"experimental": []},
                "override_always_human_domains_by_profile": {"experimental": []},
            }
        ),
        encoding="utf-8",
    )

    # profile, action=login, decision=ALLOW, tune=y, domain=forum.example, override=n, done
    inp = "experimental\nlogin\nALLOW\ny\nforum.example\nn\n(done)\n"
    subprocess.run(
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

    new_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "forum.example" in new_cfg["allowed_login_domains_by_profile"]["experimental"]
