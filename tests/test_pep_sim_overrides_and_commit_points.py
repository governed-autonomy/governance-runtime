from __future__ import annotations

from governance_runtime.pep_sim import enforce_then_call


def test_pep_sim_override_always_human_allows_login_to_be_ask_instead_of_deny():
    called = {"n": 0}

    def tool():
        called["n"] += 1
        return "LOGGED_IN"

    policy_input = {
        "request_text": "login to Gmail",
        "provenance": "USER_INTENT",
        "policy_profile": "standard",
        "action": "login",
        "effects": ["LOGIN", "CREDENTIALS"],
        "targets": {"urls": ["https://mail.google.com/mail/u/0/#inbox"]},
        "state": {"phase": "planning", "snapshot_ref": None},
    }

    cfg = {
        "always_human_domains": ["google.com"],
        "allowed_login_domains_by_profile": {"standard": ["google.com"]},
        "override_always_human_domains_by_profile": {"standard": ["google.com"]},
        "action_policies_by_profile": {
            "standard": {"purchase": "ASK", "transfer-funds": "ASK", "system-settings": "ASK", "db-delete": "ASK", "read-secrets": "DENY"}
        },
    }

    res, out = enforce_then_call(policy_input, tool, policy_config=cfg)
    assert res.kind == "ASK"
    assert out is None
    assert called["n"] == 0


def test_pep_sim_commit_point_without_snapshot_in_execution_asks():
    called = {"n": 0}

    def tool():
        called["n"] += 1
        return "CLICKED_CONFIRM"

    policy_input = {
        "request_text": "confirm purchase",
        "provenance": "USER_INTENT",
        "policy_profile": "standard",
        "action": "purchase",
        "effects": ["[MONEY]", "BROWSER_COMMIT_POINT"],
        "targets": {"urls": ["https://example.com/checkout"]},
        # execution phase + no snapshot binding should trigger commit-point ASK
        "state": {"phase": "execution", "snapshot_ref": None},
    }

    res, out = enforce_then_call(policy_input, tool)
    assert res.kind == "ASK"
    assert out is None
    assert called["n"] == 0
