from __future__ import annotations

import subprocess
import sys


def test_demo_seeded_count(tmp_path):
    out_dir = tmp_path / "receipts"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "demo",
            "--profile",
            "standard",
            "--seed",
            "123",
            "--count",
            "7",
            "--receipt-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    # base suite (6) + seeded (7)
    assert len(list(out_dir.glob("scenario_*.json"))) == 13


def test_demo_seeded_metamorphic_count(tmp_path):
    out_dir = tmp_path / "receipts"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_runtime",
            "demo",
            "--profile",
            "standard",
            "--mode",
            "metamorphic",
            "--seed",
            "123",
            "--count",
            "5",
            "--receipt-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(list(out_dir.glob("scenario_*.json"))) == 11
