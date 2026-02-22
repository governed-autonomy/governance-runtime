from governance_runtime.policy.decide import decide


def test_action_policy_config_purchase_strict_deny():
    cfg = {"action_policies_by_profile": {"strict": {"purchase": "DENY"}}}
    out = decide(
        {
            "request_text": "buy",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "action": "purchase",
            "effects": ["[MONEY]"],
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config=cfg,
    )
    assert out["decision"] == "DENY"


def test_action_policy_config_purchase_standard_ask():
    cfg = {"action_policies_by_profile": {"standard": {"purchase": "ASK"}}}
    out = decide(
        {
            "request_text": "buy",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "action": "purchase",
            "effects": ["[MONEY]"],
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config=cfg,
    )
    assert out["decision"] == "ASK"


def test_action_policy_read_secrets_standard_no_allow_clamps_to_ask():
    cfg = {"action_policies_by_profile": {"standard": {"read-secrets": "ALLOW"}}}
    out = decide(
        {
            "request_text": "read env",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "action": "read-secrets",
            "effects": ["CREDENTIALS", "[PRIVACY]"],
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config=cfg,
    )
    assert out["decision"] == "ASK"


def test_action_policy_read_secrets_strict_force_deny():
    cfg = {"action_policies_by_profile": {"strict": {"read-secrets": "ASK"}}}
    out = decide(
        {
            "request_text": "read env",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "action": "read-secrets",
            "effects": ["CREDENTIALS", "[PRIVACY]"],
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config=cfg,
    )
    assert out["decision"] == "DENY"
