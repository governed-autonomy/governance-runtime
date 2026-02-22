from governance_runtime.policy.decide import decide


def test_always_human_suffix_matches_subdomain__deny():
    out = decide(
        {
            "request_text": "Login to Gmail",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["mail.google.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={"always_human_domains": ["google.com"]},
    )
    assert out["decision"] == "DENY"


def test_allowlist_suffix_matches_subdomain__ask():
    out = decide(
        {
            "request_text": "Login to shop",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["shop.example.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": [],
            "allowed_login_domains_by_profile": {"standard": ["example.com"]},
        },
    )
    assert out["decision"] == "ASK"


def test_override_suffix_allows_always_human_domain_to_be_overridden__ask():
    out = decide(
        {
            "request_text": "Login to mail.google.com (override)",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["mail.google.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["google.com"],
            "allowed_login_domains_by_profile": {"standard": ["google.com"]},
            "override_always_human_domains_by_profile": {"standard": ["google.com"]},
        },
    )
    assert out["decision"] == "ASK"
