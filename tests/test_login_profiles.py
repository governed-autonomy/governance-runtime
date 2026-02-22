from governance_runtime.policy.decide import decide


def test_login_strict_non_allowlisted__deny():
    out = decide(
        {
            "request_text": "Login to forum",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["forum.example"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["accounts.google.com"],
            "allowed_login_domains_by_profile": {"strict": []},
        },
    )
    assert out["decision"] == "DENY"


def test_login_standard_allowlisted__ask():
    out = decide(
        {
            "request_text": "Login to forum",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["forum.example"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["accounts.google.com"],
            "allowed_login_domains_by_profile": {"standard": ["forum.example"]},
        },
    )
    assert out["decision"] == "ASK"


def test_login_standard_always_human_domain__deny():
    out = decide(
        {
            "request_text": "Login to Google",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["accounts.google.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["accounts.google.com"],
            "allowed_login_domains_by_profile": {"standard": ["accounts.google.com"]},
            "override_always_human_domains_by_profile": {"standard": []},
        },
    )
    assert out["decision"] == "DENY"


def test_login_standard_override_always_human_domain__ask():
    out = decide(
        {
            "request_text": "Login to Google (I know what I'm doing)",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["accounts.google.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={
            "always_human_domains": ["accounts.google.com"],
            "allowed_login_domains_by_profile": {"standard": ["accounts.google.com"]},
            "override_always_human_domains_by_profile": {"standard": ["accounts.google.com"]},
        },
    )
    assert out["decision"] == "ASK"
