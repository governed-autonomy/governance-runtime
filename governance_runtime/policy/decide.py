from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


DECISION_ALLOW = "ALLOW"
DECISION_ASK = "ASK"
DECISION_DENY = "DENY"


# Rule ids (stable-ish strings for receipts/tests)
R_GATE_BY_EFFECT = "R0.GATE_BY_EFFECT"
R_UNTRUSTED_NOT_INSTRUCTION = "R1.UNTRUSTED_NOT_INSTRUCTION"
R_RED_ZONE_ASK = "R2.RED_ZONE_DEFAULT_ASK"
R_SHARP_TRIAD_ASK = "R3.MONEY_PRIVACY_REPUTATION_DEFAULT_ASK"
R_COMMIT_POINT_STATE_BINDING = "R4.COMMIT_POINT_REQUIRES_STATE_BINDING"
R_ALWAYS_HUMAN_DENY = "R5.ALWAYS_HUMAN_NONDELEGABLE"
R_RECEIPTS_SHARP = "R6.RECEIPTS_REQUIRED_ON_SHARP"


# Effects tags (as strings)
E_MONEY = "[MONEY]"
E_PRIVACY = "[PRIVACY]"
E_REPUTATION = "[REPUTATION]"

E_CREDENTIALS = "CREDENTIALS"
E_LOGIN = "LOGIN"
E_EXTERNAL_COMMS = "EXTERNAL_COMMS"
E_DOWNLOAD_INSTALL = "DOWNLOAD_INSTALL"
E_DELETE_DESTRUCTIVE = "DELETE_DESTRUCTIVE"
E_EXPORT_UPLOAD = "EXPORT_UPLOAD"
E_BROWSER_COMMIT_POINT = "BROWSER_COMMIT_POINT"
E_TOOL_EXECUTION = "TOOL_EXECUTION"


DEFAULT_TTL_SECONDS = 300


def _get(obj: Dict[str, Any], path: List[str], default=None):
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _scope_from_input(policy_input: Dict[str, Any]) -> str:
    request_text = (policy_input.get("request_text") or "").strip()
    domains = _get(policy_input, ["targets", "domains"], default=None)
    tools = _get(policy_input, ["targets", "tools"], default=None)
    phase = _get(policy_input, ["state", "phase"], default=None)

    parts = []
    if request_text:
        parts.append(request_text)
    if domains:
        parts.append(f"domains={domains}")
    if tools:
        parts.append(f"tools={tools}")
    if phase:
        parts.append(f"phase={phase}")

    if not parts:
        return "Approve the described sharp action (narrow scope)"
    return " | ".join(parts)[:280]


def _domain_from_url(url: str) -> Optional[str]:
    u = (url or "").strip()
    if not u:
        return None
    # If user pastes a bare domain/path, urlparse treats it as path. Add scheme.
    if "://" not in u:
        u = "https://" + u
    p = urlparse(u)
    host = (p.hostname or "").strip().lower()
    return host or None


def _domain_matches(rule: str, domain: str) -> bool:
    """Domain match helper.

    Supports:
    - exact domain: example.com
    - suffix match (same as exact, but matches subdomains too): example.com matches a.example.com
    - explicit wildcard: *.example.com
    - leading dot: .example.com

    Note: matching is case-insensitive.
    """

    r = (rule or "").strip().lower()
    d = (domain or "").strip().lower()
    if not r or not d:
        return False

    if r.startswith("*."):
        r = r[2:]
    if r.startswith("."):
        r = r[1:]

    return d == r or d.endswith("." + r)


def _any_domain_matches(rules: List[str], domains: List[str]) -> bool:
    for d in domains:
        for r in rules:
            if _domain_matches(r, d):
                return True
    return False


def decide(policy_input: Dict[str, Any], policy_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic policy decision.

    Input/output is JSON-serializable dicts per spec.

    Note: MVP behavior is conservative. We can refine DENY/ASK logic with
    explicit allowlists and better target classification.
    """

    provenance = policy_input.get("provenance")
    effects: List[str] = list(policy_input.get("effects") or [])

    policy_profile = (policy_input.get("policy_profile") or "strict").lower()
    action = (policy_input.get("action") or "").strip().lower() or None

    # Targets: allow either explicit domains or URLs (we derive domains from URLs).
    domains: List[str] = [d.lower() for d in list(_get(policy_input, ["targets", "domains"], default=[]) or [])]
    urls: List[str] = list(_get(policy_input, ["targets", "urls"], default=[]) or [])
    if urls:
        for u in urls:
            d = _domain_from_url(u)
            if d:
                domains.append(d)
    # De-dupe while preserving order
    seen = set()
    domains = [d for d in domains if not (d in seen or seen.add(d))]

    cfg = policy_config or {}

    # Built-in defaults (used when config omits these sections).
    default_action_policies_by_profile = {
        "strict": {
            "purchase": "DENY",
            "transfer-funds": "DENY",
            "system-settings": "DENY",
            "db-delete": "DENY",
            "read-secrets": "DENY",
        },
        "tight": {
            "purchase": "DENY",
            "transfer-funds": "DENY",
            "system-settings": "DENY",
            "db-delete": "DENY",
            "read-secrets": "DENY",
        },
        "standard": {
            "purchase": "ASK",
            "transfer-funds": "ASK",
            "system-settings": "ASK",
            "db-delete": "ASK",
            "read-secrets": "DENY",
        },
        "experimental": {
            "purchase": "ASK",
            "transfer-funds": "ASK",
            "system-settings": "ASK",
            "db-delete": "ASK",
            "read-secrets": "DENY",
        },
    }

    # Merge defaults with config overrides.
    merged_action_policies = dict(default_action_policies_by_profile)
    cfg_action_policies_in = cfg.get("action_policies_by_profile") or {}
    if isinstance(cfg_action_policies_in, dict):
        for prof, rules in cfg_action_policies_in.items():
            if not isinstance(rules, dict):
                continue
            base = dict(merged_action_policies.get(prof, {}))
            base.update(rules)
            merged_action_policies[prof] = base

    always_human_domains = list(cfg.get("always_human_domains") or [])
    allowed_login_domains_by_profile = (cfg.get("allowed_login_domains_by_profile") or {})
    override_always_human_domains_by_profile = list(
        (cfg.get("override_always_human_domains_by_profile") or {}).get(policy_profile, [])
    )

    allowed_login_domains = list(allowed_login_domains_by_profile.get(policy_profile) or [])

    phase = _get(policy_input, ["state", "phase"], default="planning")
    snapshot_ref = _get(policy_input, ["state", "snapshot_ref"], default=None)

    # Base receipts always include these fields.
    required_receipts = ["provenance", "effects", "reasons"]
    reasons: List[str] = [R_GATE_BY_EFFECT]

    # Untrusted context is never an instruction.
    if provenance in ("UNTRUSTED_CONTEXT", "TOOL_OUTPUT"):
        reasons.append(R_UNTRUSTED_NOT_INSTRUCTION)

    # Special-case: imperatives inside UNTRUSTED_CONTEXT/TOOL_OUTPUT are non-executable.
    # If they request a privileged tool execution, DENY executing that instruction.
    if provenance in ("UNTRUSTED_CONTEXT", "TOOL_OUTPUT") and E_TOOL_EXECUTION in effects:
        reasons.append("RZ.UNTRUSTED_TOOL_EXECUTION_DENY")
        return {
            "decision": DECISION_DENY,
            "reasons": reasons,
            "required_receipts": sorted(set(required_receipts + ["request_text", "targets", "policy_profile"])) ,
            "required_approval": None,
        }

    # Special-case: destructive commands suggested by TOOL_OUTPUT should not be executed.
    # (We can still ASK the user for an alternative safe plan; this decision is about
    # executing the suggested destructive step.)
    if provenance == "TOOL_OUTPUT" and E_DELETE_DESTRUCTIVE in effects:
        reasons.append("RZ.TOOL_OUTPUT_DESTRUCTIVE_DENY")
        return {
            "decision": DECISION_DENY,
            "reasons": reasons,
            "required_receipts": sorted(set(required_receipts + ["request_text", "targets", "policy_profile"])) ,
            "required_approval": None,
        }

    has_sharp_triad = any(e in effects for e in (E_MONEY, E_PRIVACY, E_REPUTATION))

    # Action-level policy overrides (config-driven).
    # These are intended to make experimental/standard tunable without code changes.
    action_policy = None
    if action:
        action_policy = (merged_action_policies.get(policy_profile) or {}).get(action)

    # Guardrails on how much profiles are allowed to loosen certain actions.
    # - strict/tight: read-secrets must remain DENY
    # - standard: read-secrets can be DENY or ASK (never ALLOW)
    if action == "read-secrets":
        if policy_profile in ("strict", "tight") and action_policy and action_policy != DECISION_DENY:
            reasons.append("POLICY.GUARD.READ_SECRETS_STRICT_FORCE_DENY")
            action_policy = DECISION_DENY
        if policy_profile == "standard" and action_policy == DECISION_ALLOW:
            reasons.append("POLICY.GUARD.READ_SECRETS_STANDARD_NO_ALLOW")
            action_policy = DECISION_ASK

    if action_policy in (DECISION_ALLOW, DECISION_ASK, DECISION_DENY):
        reasons.append(f"POLICY.CONFIG.ACTION_POLICY[{policy_profile}][{action}]={action_policy}")
        if action_policy == DECISION_ALLOW:
            # continue with normal evaluation (ALLOW here means no special override)
            pass
        elif action_policy == DECISION_DENY:
            return {
                "decision": DECISION_DENY,
                "reasons": reasons,
                "required_receipts": sorted(
                    set(required_receipts + ["request_text", "targets", "policy_profile", "action"])
                ),
                "required_approval": None,
            }
        elif action_policy == DECISION_ASK:
            reasons.append(R_RECEIPTS_SHARP)
            required_receipts2 = sorted(
                set(required_receipts + ["request_text", "targets", "state", "policy_profile", "action"])
            )
            return {
                "decision": DECISION_ASK,
                "reasons": reasons,
                "required_receipts": required_receipts2,
                "required_approval": {
                    "required": True,
                    "token_schema": "approval_token_schema_v0.md",
                    "ttl_seconds": DEFAULT_TTL_SECONDS,
                    "scope": _scope_from_input(policy_input),
                    "state_binding": {
                        "snapshot_ref": snapshot_ref,
                        "phase": "commit_point" if phase == "commit_point" else phase,
                    },
                },
            }

    # LOGIN/CREDENTIALS handling with allowlists + per-profile overrides.
    if E_LOGIN in effects or E_CREDENTIALS in effects:
        required_receipts = sorted(set(required_receipts + ["request_text", "targets", "policy_profile", "action"]))

        # If we know the domain and it's always-human (unless overridden), DENY.
        if domains and _any_domain_matches(always_human_domains, domains) and not _any_domain_matches(
            override_always_human_domains_by_profile, domains
        ):
            reasons.append(R_ALWAYS_HUMAN_DENY)
            return {
                "decision": DECISION_DENY,
                "reasons": reasons,
                "required_receipts": required_receipts,
                "required_approval": None,
            }

        # Allowlisted login domains (per profile) -> ASK (bounded approval), else DENY.
        if domains and _any_domain_matches(allowed_login_domains, domains):
            # Treat as sharp (requires approval + receipts).
            reasons.append("RZ.LOGIN_ALLOWLIST_DEFAULT_ASK")
            reasons.append(R_RECEIPTS_SHARP)
            required_receipts = sorted(set(required_receipts + ["state"]))
            return {
                "decision": DECISION_ASK,
                "reasons": reasons,
                "required_receipts": required_receipts,
                "required_approval": {
                    "required": True,
                    "token_schema": "approval_token_schema_v0.md",
                    "ttl_seconds": DEFAULT_TTL_SECONDS,
                    "scope": _scope_from_input(policy_input),
                    "state_binding": {
                        "snapshot_ref": snapshot_ref,
                        "phase": "commit_point" if phase == "commit_point" else phase,
                    },
                },
            }

        # No domain info or not allowlisted -> DENY by default.
        reasons.append("RZ.LOGIN_DEFAULT_DENY")
        return {
            "decision": DECISION_DENY,
            "reasons": reasons,
            "required_receipts": required_receipts,
            "required_approval": None,
        }

    # Red zone effects default to ASK
    red_zone_effects = {
        E_EXTERNAL_COMMS,
        E_EXPORT_UPLOAD,
        E_DOWNLOAD_INSTALL,
        E_DELETE_DESTRUCTIVE,
        E_TOOL_EXECUTION,
    }
    if red_zone_effects.intersection(effects):
        reasons.append(R_RED_ZONE_ASK)

    # MONEY/PRIVACY/REPUTATION default to ASK
    if has_sharp_triad:
        reasons.append(R_SHARP_TRIAD_ASK)

    # Commit point: must have snapshot_ref
    if E_BROWSER_COMMIT_POINT in effects:
        if phase != "commit_point" or not snapshot_ref:
            reasons.append(R_COMMIT_POINT_STATE_BINDING)

    needs_ask = any(
        r in reasons
        for r in (
            R_RED_ZONE_ASK,
            R_SHARP_TRIAD_ASK,
            R_COMMIT_POINT_STATE_BINDING,
        )
    )

    if needs_ask:
        reasons.append(R_RECEIPTS_SHARP)
        required_receipts = sorted(set(required_receipts + ["request_text", "targets", "state", "policy_profile", "action"]))
        return {
            "decision": DECISION_ASK,
            "reasons": reasons,
            "required_receipts": required_receipts,
            "required_approval": {
                "required": True,
                "token_schema": "approval_token_schema_v0.md",
                "ttl_seconds": DEFAULT_TTL_SECONDS,
                "scope": _scope_from_input(policy_input),
                "state_binding": {
                    "snapshot_ref": snapshot_ref,
                    "phase": "commit_point" if phase == "commit_point" else phase,
                },
            },
        }

    return {
        "decision": DECISION_ALLOW,
        "reasons": reasons,
        "required_receipts": sorted(set(required_receipts + ["policy_profile", "action"])),
        "required_approval": None,
    }
