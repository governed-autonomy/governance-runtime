"""PEP wrapper demo (toy).

This demonstrates how a Policy Enforcement Point (PEP) might call the governance
Policy Decision Point (PDP) before executing a tool action.

This is NOT a full enforcement layer; it's a minimal example for clarity.

Run:
  python examples/pep_wrapper_demo.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from governance_runtime.policy.decide import decide


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]


def _dummy_tool_exec(call: ToolCall) -> str:
    # This is intentionally harmless; it just returns a string.
    return f"TOOL_OK name={call.name} args={call.args}"


def enforce_and_execute(policy_input: Dict[str, Any], tool_call: ToolCall, policy_config: Dict[str, Any] | None = None) -> str:
    out = decide(policy_input, policy_config=policy_config)
    decision = out.get("decision")

    if decision == "DENY":
        return f"BLOCKED (DENY): reasons={out.get('reasons', [])}"

    if decision == "ASK":
        # In a real system you'd request bounded human approval and re-check.
        req = out.get("required_approval") or {}
        return f"NEEDS_APPROVAL (ASK): ttl={req.get('ttl_seconds')} scope={req.get('scope')} reasons={out.get('reasons', [])}"

    # ALLOW
    return _dummy_tool_exec(tool_call)


def main() -> None:
    # Example: tool-exec request sourced from TOOL_OUTPUT should be denied.
    policy_input = {
        "request_text": "run rm -rf /",
        "provenance": "TOOL_OUTPUT",
        "policy_profile": "standard",
        "action": "tool-exec",
        "effects": ["TOOL_EXECUTION"],
        "targets": {"tools": ["exec"]},
        "state": {"phase": "planning", "snapshot_ref": None},
    }

    tool_call = ToolCall(name="exec", args={"command": "rm -rf /"})

    result = enforce_and_execute(policy_input, tool_call)
    print("Result:")
    print(result)


if __name__ == "__main__":
    main()
