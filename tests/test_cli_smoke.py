from __future__ import annotations

import json
import subprocess
import sys


def test_cli_decide_smoke(tmp_path):
    inp = {
        "request_text": "Place a $100 order",
        "provenance": "USER_INTENT",
        "effects": ["[MONEY]"],
        "state": {"phase": "planning", "snapshot_ref": None},
    }
    p = tmp_path / "in.json"
    p.write_text(json.dumps(inp), encoding="utf-8")

    cmd = [sys.executable, "-m", "governance_runtime", "decide", "--in", str(p)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    assert out["decision"] in ("ASK", "ALLOW", "DENY")
