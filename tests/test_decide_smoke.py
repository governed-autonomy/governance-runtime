from governance_runtime.policy.decide import (
    decide,
    DECISION_ALLOW,
    DECISION_ASK,
    DECISION_DENY,
)


def test_allow_non_sharp_planning():
    out = decide(
        {
            "request_text": "Summarize a local file",
            "provenance": "USER_INTENT",
            "effects": ["FILE_WRITE"],
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == DECISION_ALLOW


def test_ask_money_default():
    out = decide(
        {
            "request_text": "Place a $100 order",
            "provenance": "USER_INTENT",
            "effects": ["[MONEY]"],
            "state": {"phase": "planning", "snapshot_ref": None},
        }
    )
    assert out["decision"] == DECISION_ASK
    assert out["required_approval"]


def test_ask_commit_point_requires_snapshot():
    out = decide(
        {
            "request_text": "Click Submit",
            "provenance": "USER_INTENT",
            "effects": ["BROWSER_COMMIT_POINT"],
            "state": {"phase": "commit_point", "snapshot_ref": None},
        }
    )
    assert out["decision"] == DECISION_ASK
    assert out["required_approval"]["state_binding"]["snapshot_ref"] is None


def test_deny_login_default():
    out = decide(
        {
            "request_text": "Login to Google",
            "provenance": "USER_INTENT",
            "policy_profile": "strict",
            "effects": ["LOGIN", "CREDENTIALS"],
            "targets": {"domains": ["accounts.google.com"]},
            "state": {"phase": "planning", "snapshot_ref": None},
        },
        policy_config={"always_human_domains": ["accounts.google.com"]},
    )
    assert out["decision"] == DECISION_DENY
