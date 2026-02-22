from __future__ import annotations

import subprocess
import sys


def test_doctor_smoke(tmp_path):
    out_dir = tmp_path / "doctor_receipts"
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "doctor",
            "--receipt-dir",
            str(out_dir),
            "--seed",
            "123",
            "--count",
            "3",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "governance doctor" in res.stdout
    assert out_dir.exists()
    # base (1) + seeded (3)
    assert len(list(out_dir.glob("scenario_*.json"))) == 4
