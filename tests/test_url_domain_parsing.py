from governance_runtime.policy.decide import decide


def test_targets_urls_extracts_domain_and_enforces_always_human():
    out = decide(
        {
            "request_text": "Login to Gmail",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"urls": ["https://mail.google.com/mail/u/0/#inbox"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={"always_human_domains": ["mail.google.com"]},
    )
    assert out["decision"] == "DENY"


def test_targets_urls_bare_domain_is_supported():
    out = decide(
        {
            "request_text": "Login to forum",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"urls": ["forum.example/login"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["mail.google.com"],
            "allowed_login_domains_by_profile": {"standard": ["forum.example"]},
        },
    )
    assert out["decision"] == "ASK"
