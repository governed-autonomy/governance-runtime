"""Toy PEP (Policy Enforcement Point) simulation helpers.

This module exists to test the *enforcement seam* without executing real tools.

- PDP (Policy Decision Point) = governance_runtime.policy.decide.decide
- PEP (Policy Enforcement Point) = code that asks the PDP, then enforces ALLOW/ASK/DENY

This is intentionally minimal and safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from governance_runtime.policy.decide import decide


@dataclass
class PepResult:
    kind: str  # ALLOW|ASK|DENY
    detail: str
    decision_output: Dict[str, Any]


def enforce(
    policy_input: Dict[str, Any],
    policy_config: Optional[Dict[str, Any]] = None,
) -> PepResult:
    out = decide(policy_input, policy_config=policy_config)
    decision = out.get("decision")

    if decision == "DENY":
        return PepResult(kind="DENY", detail="blocked", decision_output=out)

    if decision == "ASK":
        req = out.get("required_approval") or {}
        detail = f"needs_approval ttl={req.get('ttl_seconds')}"
        return PepResult(kind="ASK", detail=detail, decision_output=out)

    return PepResult(kind="ALLOW", detail="allowed", decision_output=out)


def enforce_then_call(
    policy_input: Dict[str, Any],
    tool_fn: Callable[[], Any],
    policy_config: Optional[Dict[str, Any]] = None,
) -> tuple[PepResult, Any | None]:
    """Enforce PDP decision; call tool_fn only on ALLOW.

    Returns (pep_result, tool_output_or_none).
    """

    res = enforce(policy_input, policy_config=policy_config)
    if res.kind != "ALLOW":
        return res, None
    return res, tool_fn()
