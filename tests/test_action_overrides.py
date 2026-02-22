from governance_runtime.policy.decide import decide


def test_purchase_strict_denies_when_action_present():
    out = decide(
        {
            "request_text": "Buy something",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "action": "purchase",
            "effects": ["[MONEY]", "BROWSER_COMMIT_POINT"],
            "targets": {"urls": ["https://shop.example/checkout"]},
            "state": {"phase": "commit_point", "snapshot_ref": "snap"},
        }
    )
    assert out["decision"] == "DENY"


def test_purchase_standard_still_asks():
    out = decide(
        {
            "request_text": "Buy something",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "action": "purchase",
            "effects": ["[MONEY]", "BROWSER_COMMIT_POINT"],
            "targets": {"urls": ["https://shop.example/checkout"]},
            "state": {"phase": "commit_point", "snapshot_ref": "snap"},
        }
    )
    assert out["decision"] == "ASK"


def test_read_secrets_denies_by_default():
    out = decide(
        {
            "request_text": "Read .env",
            "provenance": "USER_INTENT",
            "policy_profile": "experimental",
            "action": "read-secrets",
            "effects": ["CREDENTIALS", "[PRIVACY]"],
            "targets": {},
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == "DENY"
