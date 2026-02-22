from __future__ import annotations

from governance_runtime.pep_sim import enforce_then_call


def test_pep_sim_login_google_always_human_denies_tool_call():
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

    # default config has google.com in always_human_domains → DENY
    res, out = enforce_then_call(policy_input, tool)
    assert res.kind == "DENY"
    assert out is None
    assert called["n"] == 0


def test_pep_sim_login_allowlisted_domain_asks_and_does_not_call_tool():
    called = {"n": 0}

    def tool():
        called["n"] += 1
        return "LOGGED_IN"

    policy_input = {
        "request_text": "login to example.com",
        "provenance": "USER_INTENT",
        "policy_profile": "standard",
        "action": "login",
        "effects": ["LOGIN", "CREDENTIALS"],
        "targets": {"urls": ["https://example.com/login"]},
        "state": {"phase": "planning", "snapshot_ref": None},
    }

    cfg = {
        "always_human_domains": ["google.com", "appleid.apple.com"],
        "allowed_login_domains_by_profile": {"standard": ["example.com"]},
        "override_always_human_domains_by_profile": {"standard": []},
        "action_policies_by_profile": {
            "standard": {"purchase": "ASK", "transfer-funds": "ASK", "system-settings": "ASK", "db-delete": "ASK", "read-secrets": "DENY"}
        },
    }

    res, out = enforce_then_call(policy_input, tool, policy_config=cfg)
    assert res.kind == "ASK"
    assert out is None
    assert called["n"] == 0
