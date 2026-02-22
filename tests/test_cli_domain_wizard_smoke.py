from __future__ import annotations

import json
import subprocess
import sys


def test_domain_wizard_adds_always_human(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"always_human_domains": []}), encoding="utf-8")

    # Feed: operation, domain, done
    inp = "always-human add\nexample.com\n(done)\n"
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "domain-wizard",
            "--config",
            str(cfg_path),
        ],
        input=inp,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "OK: always_human_domains" in res.stdout
    new_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "example.com" in new_cfg["always_human_domains"]
