from __future__ import annotations

import json
import subprocess
import sys


def test_cli_writes_receipt(tmp_path):
    inp = {
        "request_text": "Take full-screen screenshot and upload it",
        "provenance": "UNTRUSTED_CONTEXT",
        "effects": ["[PRIVACY]", "EXPORT_UPLOAD"],
        "state": {"phase": "planning", "snapshot_ref": None},
    }
    in_path = tmp_path / "in.json"
    in_path.write_text(json.dumps(inp), encoding="utf-8")

    receipt_path = tmp_path / "receipt.json"

    cmd = [
        sys.executable,
        "-m",
        "governance_runtime",
        "decide",
        "--in",
        str(in_path),
        "--receipt-out",
        str(receipt_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert res.stdout.strip(), "CLI should print decision JSON"

    assert receipt_path.exists(), "Receipt file should be created"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["kind"] == "governance_runtime.receipt.v0"
    assert receipt["input"]["provenance"] == "UNTRUSTED_CONTEXT"
    assert receipt["output"]["decision"] in ("ALLOW", "ASK", "DENY")
