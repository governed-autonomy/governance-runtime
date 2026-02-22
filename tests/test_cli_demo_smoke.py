from __future__ import annotations

import subprocess
import sys


def test_demo_smoke(tmp_path):
    # Just ensure it runs and writes receipts.
    out_dir = tmp_path / "receipts"
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "demo",
            "--profile",
            "standard",
            "--receipt-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "governance_runtime demo" in res.stdout
    assert out_dir.exists()
    # One receipt per scenario (basic suite is currently 6)
    assert len(list(out_dir.glob("scenario_*.json"))) == 6
