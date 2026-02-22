from governance_runtime.policy.decide import decide


def test_system_settings_strict_denies():
    out = decide(
        {
            "request_text": "Turn off firewall",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "action": "system-settings",
            "effects": ["TOOL_EXECUTION"],
            "targets": {},
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == "DENY"


def test_db_delete_strict_denies():
    out = decide(
        {
            "request_text": "Delete old rows from database",
            "provenance": "USER_INTENT",
            "policy_profile": "tight",
            "action": "db-delete",
            "effects": ["DELETE_DESTRUCTIVE", "[PRIVACY]"],
            "targets": {},
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == "DENY"


def test_transfer_funds_strict_denies():
    out = decide(
        {
            "request_text": "Transfer crypto",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "action": "transfer-funds",
            "effects": ["[MONEY]"],
            "targets": {},
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == "DENY"


def test_transfer_funds_standard_asks():
    out = decide(
        {
            "request_text": "Transfer crypto",
            "provenance": "USER_INTENT",
            "policy_profile": "standard",
            "action": "transfer-funds",
            "effects": ["[MONEY]"],
            "targets": {},
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == "ASK"
