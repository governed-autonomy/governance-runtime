from __future__ import annotations

import subprocess
import sys


def test_wizard_smoke_runs_and_outputs_decision(tmp_path):
    # Feed: mode, action, URLs, blank line
    inp = "experimental\nlogin\nhttps://mail.google.com/\n\n"
    res = subprocess.run(
        [sys.executable, "-m", "governance_runtime", "wizard"],
        input=inp,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "\"decision\"" in res.stdout
    assert "Decision:" in res.stdout
