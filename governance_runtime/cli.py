from __future__ import annotations

import argparse
import json
import os
import random
import sys
from typing import Any, Dict

from datetime import datetime, timezone
from pathlib import Path

from governance_runtime.policy.decide import decide


def _load_json(path: str | None) -> Dict[str, Any]:
    if not path or path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


ACTION_EFFECTS = {
    # Minimal v0 mapping: helps avoid user mis-tagging.
    "login": ["LOGIN", "CREDENTIALS"],
    "send-message": ["EXTERNAL_COMMS"],
    "purchase": ["[MONEY]", "BROWSER_COMMIT_POINT"],
    "transfer-funds": ["[MONEY]", "BROWSER_COMMIT_POINT"],
    "upload": ["EXPORT_UPLOAD", "[PRIVACY]"],
    "download": ["DOWNLOAD_INSTALL"],
    "delete": ["DELETE_DESTRUCTIVE"],
    "db-delete": ["DELETE_DESTRUCTIVE", "[PRIVACY]"],
    "system-settings": ["TOOL_EXECUTION"],
    "tool-exec": ["TOOL_EXECUTION"],
    "read-secrets": ["CREDENTIALS", "[PRIVACY]"],
}


def _build_input_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    targets: Dict[str, Any] = {}
    if args.url:
        targets["urls"] = [args.url]

    if args.effects is not None:
        effects = args.effects
    elif args.action:
        effects = ACTION_EFFECTS.get(args.action, [])
    else:
        effects = []

    req = args.request_text
    if not req:
        if args.action and args.url:
            req = f"{args.action} @ {args.url}"
        elif args.action:
            req = args.action
        elif args.url:
            req = f"Decide for url={args.url}"
        else:
            req = ""

    return {
        "request_text": req,
        "provenance": args.provenance or "USER_INTENT",
        "policy_profile": args.profile or "strict",
        "action": args.action,
        "effects": effects,
        "targets": targets or {},
        "state": {"phase": "planning", "snapshot_ref": None},
    }


DEFAULT_CONFIG_REL = "config/policy_config_default_v0.json"
ENV_CONFIG_KEY = "GOVERNANCE_CONFIG"


def _resolve_config_path(cli_path: str | None) -> str | None:
    # Precedence: CLI flag > env var > local default
    if cli_path:
        return cli_path
    env = (os.environ.get(ENV_CONFIG_KEY) or "").strip()
    if env:
        return env
    local = Path(DEFAULT_CONFIG_REL)
    if local.exists():
        return str(local)
    return None


def _load_config(path: str | None) -> Dict[str, Any] | None:
    if not path:
        return None
    return _load_json(path)


def _save_json(path: str, obj: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_config_receipt(cfg_path: str, cmd: str, change: Dict[str, Any]) -> None:
    from governance_runtime.version import __version__

    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    out_dir = Path("receipts")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"config_change_{ts}.json"

    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": "governance_runtime.config_change.v0",
        "version": __version__,
        "command": cmd,
        "config_path": cfg_path,
        "change": change,
    }
    p.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dedupe(seq: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for s in seq:
        s2 = (s or "").strip()
        if not s2:
            continue
        if s2 not in seen:
            seen.add(s2)
            out.append(s2)
    return out


def _ensure_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _explain(policy_input: Dict[str, Any], policy_output: Dict[str, Any], policy_config: Dict[str, Any] | None) -> str:
    decision = policy_output.get("decision")
    reasons = list(policy_output.get("reasons") or [])
    url = None
    try:
        url = (policy_input.get("targets") or {}).get("urls", [None])[0]
    except Exception:
        url = None

    # Minimal reason-to-text mapping.
    mapping = {
        "R0.GATE_BY_EFFECT": "Decision is based on effect tags (not keywords).",
        "R1.UNTRUSTED_NOT_INSTRUCTION": "Untrusted/tool output is treated as data, not an instruction.",
        "R2.RED_ZONE_DEFAULT_ASK": "This action hits a red-zone effect → requires explicit approval.",
        "R3.MONEY_PRIVACY_REPUTATION_DEFAULT_ASK": "Money/privacy/reputation effects are sharp → requires approval.",
        "R4.COMMIT_POINT_REQUIRES_STATE_BINDING": "Commit point requires a state snapshot binding.",
        "R5.ALWAYS_HUMAN_NONDELEGABLE": "Target matches an always-human domain (non-delegable by default).",
        "RZ.LOGIN_DEFAULT_DENY": "Logins are denied by default unless allowlisted for this profile.",
        "RZ.LOGIN_ALLOWLIST_DEFAULT_ASK": "Login domain is allowlisted for this profile → allowed with approval (ASK).",
        "RZ.UNTRUSTED_TOOL_EXECUTION_DENY": "Refusing to execute tool instructions sourced from untrusted/tool output.",
        "RZ.TOOL_OUTPUT_DESTRUCTIVE_DENY": "Refusing destructive actions suggested by tool output.",
    }

    lines = []
    if url:
        lines.append(f"Target: {url}")
    lines.append(f"Decision: {decision}")

    # Pick 2–4 most informative reasons.
    informative = [r for r in reasons if r in mapping]
    if informative:
        lines.append("Why:")
        for r in informative[:4]:
            lines.append(f"- {mapping[r]}")
    else:
        lines.append(f"Reasons: {reasons}")

    if decision == "ASK":
        ttl = (policy_output.get("required_approval") or {}).get("ttl_seconds")
        if ttl:
            lines.append(f"Approval TTL: {ttl}s")

    return "\n".join(lines)


def _prompt(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    sys.stdout.write(prompt + suffix + ": ")
    sys.stdout.flush()
    s = sys.stdin.readline()
    if s is None:
        return default or ""
    s = s.strip()
    return s if s else (default or "")


def _prompt_choice(prompt: str, choices: list[str], default: str) -> str:
    cset = {c.lower(): c for c in choices}
    while True:
        s = _prompt(prompt, default)
        if not s:
            s = default
        key = s.strip().lower()
        if key in cset:
            return cset[key]
        sys.stdout.write(f"Invalid choice. Options: {', '.join(choices)}\n")


def _write_receipt(path: str, policy_input: Dict[str, Any], policy_output: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    from governance_runtime.version import __version__

    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": "governance_runtime.receipt.v0",
        "version": __version__,
        "input": policy_input,
        "output": policy_output,
    }

    p.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="governance", description="Governance runtime MVP CLI")
    p.add_argument("--version", action="store_true", help="Show version and exit")
    sub = p.add_subparsers(dest="cmd", required=False)

    p_decide = sub.add_parser("decide", help="Run policy decision")
    p_decide.add_argument("--in", dest="in_path", default=None, help="Input JSON path, or '-' for stdin")

    # Sugar: allow users to avoid JSON for simple cases.
    p_decide.add_argument("--url", dest="url", default=None, help="Target URL (sugar; builds input JSON)")
    p_decide.add_argument(
        "--effects",
        dest="effects",
        nargs="+",
        default=None,
        help="Effects tags (advanced). If omitted, you can use --action.",
    )
    p_decide.add_argument(
        "--action",
        dest="action",
        default=None,
        choices=[
            "login",
            "send-message",
            "purchase",
            "upload",
            "download",
            "delete",
            "tool-exec",
            "read-secrets",
            "system-settings",
            "db-delete",
            "transfer-funds",
        ],
        help="Simple action type (recommended) to derive effects automatically.",
    )
    p_decide.add_argument(
        "--profile",
        dest="profile",
        default=None,
        help="Policy profile (sugar), e.g. strict|standard|experimental",
    )
    p_decide.add_argument(
        "--provenance",
        dest="provenance",
        default=None,
        help="Provenance (sugar), e.g. USER_INTENT|UNTRUSTED_CONTEXT|TOOL_OUTPUT",
    )
    p_decide.add_argument(
        "--request",
        dest="request_text",
        default=None,
        help="Request text (sugar).",
    )

    p_decide.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    p_decide.add_argument("--explain", action="store_true", help="Print a short human explanation")
    p_decide.add_argument(
        "--receipt-out",
        dest="receipt_out",
        default=None,
        help="Optional path to write a receipt JSON (input + output + timestamp)",
    )
    p_decide.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default: ./config/policy_config_default_v0.json or $GOVERNANCE_CONFIG)",
    )

    p_init = sub.add_parser("init", help="Initialize a default policy config in ./config/")
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config file if it exists",
    )

    p_wiz = sub.add_parser("wizard", help="Interactive wizard for running decisions")
    
    p_pw = sub.add_parser("policy-wizard", help="Interactive wizard for tuning action policy decisions")
    p_pw.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )

    p_dw = sub.add_parser("domain-wizard", help="Interactive wizard for tuning domain allowlists/overrides")
    p_dw.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )
    p_wiz.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )
    p_wiz.add_argument(
        "--receipt-dir",
        dest="receipt_dir",
        default=None,
        help="Optional directory to write decision receipts (one per URL)",
    )

    p_ps = sub.add_parser("policy-show", help="Show the effective action policy table for a profile")
    p_ps.add_argument("--profile", default="experimental", help="strict|standard|experimental")
    p_ps.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )

    p_demo = sub.add_parser("demo", help="Run a proof-on-demand demo (prints decisions + optional receipts)")
    p_demo.add_argument("--profile", default="standard", help="strict|standard|experimental")
    p_demo.add_argument(
        "--mode",
        default="showcase",
        choices=["showcase", "metamorphic"],
        help="Demo mode. showcase=mixed outcomes; metamorphic=wording variations intended not to change decisions.",
    )
    p_demo.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output (prints detailed explanations per scenario).",
    )
    p_demo.add_argument(
        "--extended",
        action="store_true",
        help="Run a larger fixed demo suite in addition to the basic scenarios.",
    )
    p_demo.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG seed for generating deterministic additional scenarios.",
    )
    p_demo.add_argument(
        "--count",
        type=int,
        default=20,
        help="Number of seeded scenarios to generate (used only with --seed).",
    )
    p_demo.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )
    p_demo.add_argument(
        "--receipt-dir",
        dest="receipt_dir",
        default=None,
        help="Optional directory to write receipts (default: ./runs/demo_<timestamp>/)",
    )

    p_doc = sub.add_parser("doctor", help="Environment self-check: version, python, config, and a quick demo run")
    p_doc.add_argument("--profile", default="standard", help="strict|standard|experimental")
    p_doc.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default resolution rules apply)",
    )
    p_doc.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Seed for the quick demo check (default: 123)",
    )
    p_doc.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of seeded scenarios for the quick demo check (default: 5)",
    )
    p_doc.add_argument(
        "--receipt-dir",
        dest="receipt_dir",
        default=None,
        help="Optional directory for demo receipts (default: ./runs/doctor_<timestamp>/)",
    )

    p_show = sub.add_parser("config-show", help="Print the resolved policy config (path + JSON)")

    p_reset = sub.add_parser("config-reset", help="Reset config to defaults (writes ./config/policy_config_default_v0.json)")
    p_reset.add_argument("--force", action="store_true", help="Overwrite existing config")
    p_reset.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional config JSON path (default resolution rules apply)",
    )

    p_rm = sub.add_parser("config-remove", help="Remove a domain from config lists")
    p_rm.add_argument(
        "--field",
        required=True,
        choices=["always-human", "allow-login", "override-always-human"],
        help="Which list to remove from",
    )
    p_rm.add_argument("--domain", required=True, help="Domain/suffix rule to remove")
    p_rm.add_argument("--profile", default=None, help="Profile (required for allow-login/override-always-human)")
    p_rm.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional config JSON path (default resolution rules apply)",
    )
    p_show.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Optional policy config JSON path (default: ./config/policy_config_default_v0.json or $GOVERNANCE_CONFIG)",
    )

    # Minimal config-management commands (public-friendly)
    p_al = sub.add_parser("allow-login", help="Allow site-native logins for a domain in a profile (ASK, not ALLOW)")
    p_al.add_argument("--profile", required=True, help="strict|standard|experimental")
    p_al.add_argument("--domain", required=True, help="Domain or suffix rule (e.g. example.com)")
    p_al.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Config JSON path (default: ./config/policy_config_default_v0.json or $GOVERNANCE_CONFIG)",
    )

    p_ah = sub.add_parser("always-human", help="Add a domain to always-human (non-delegable by default)")
    p_ah.add_argument("--domain", required=True, help="Domain or suffix rule (e.g. google.com)")
    p_ah.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Config JSON path (default: ./config/policy_config_default_v0.json or $GOVERNANCE_CONFIG)",
    )

    p_ov = sub.add_parser(
        "override-always-human",
        help="Override always-human for a specific profile + domain (makes it delegable via allow-login -> ASK)",
    )
    p_ov.add_argument("--profile", required=True, help="strict|standard|experimental")
    p_ov.add_argument("--domain", required=True, help="Domain or suffix rule")
    p_ov.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Config JSON path (default: ./config/policy_config_default_v0.json or $GOVERNANCE_CONFIG)",
    )

    args = p.parse_args(argv)

    if args.version:
        from governance_runtime.version import __version__

        sys.stdout.write(__version__ + "\n")
        return 0

    if not getattr(args, "cmd", None):
        p.error("the following arguments are required: cmd")

    if args.cmd == "policy-wizard":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            cfg_path = DEFAULT_CONFIG_REL

        cfg = _load_config(cfg_path)
        if cfg is None:
            cfg = {}
        cfg = _ensure_dict(cfg)

        sys.stdout.write(f"Policy config: {cfg_path}\n")

        profile = _prompt_choice("Profile", ["strict", "standard", "experimental"], "experimental")

        changed = []

        while True:
            action = _prompt_choice(
                "Action",
                [
                    "login",
                    "send-message",
                    "purchase",
                    "transfer-funds",
                    "upload",
                    "download",
                    "delete",
                    "db-delete",
                    "system-settings",
                    "tool-exec",
                    "read-secrets",
                    "(done)",
                ],
                "purchase",
            )
            if action == "(done)":
                break

            decision = _prompt_choice("Set decision for this action", ["ALLOW", "ASK", "DENY"], "ASK")

            # Enforce the guardrails the engine enforces (so users see it immediately).
            if action == "read-secrets" and profile in ("strict", "tight"):
                decision = "DENY"
                sys.stdout.write("Note: read-secrets is forced to DENY in strict/tight profiles.\n")
            if action == "read-secrets" and profile == "standard" and decision == "ALLOW":
                decision = "ASK"
                sys.stdout.write("Note: standard profile cannot set read-secrets to ALLOW; clamped to ASK.\n")

            apbp = _ensure_dict(cfg.get("action_policies_by_profile"))
            prof_rules = _ensure_dict(apbp.get(profile))
            prof_rules[action] = decision
            apbp[profile] = prof_rules
            cfg["action_policies_by_profile"] = apbp

            _save_json(cfg_path, cfg)
            _write_config_receipt(
                cfg_path,
                "policy-wizard",
                {"profile": profile, "action": action, "decision": decision},
            )

            sys.stdout.write(f"OK: action_policies_by_profile[{profile}][{action}] = {decision}\n")
            if action == "login":
                sys.stdout.write(
                    "Note: LOGIN can still be constrained by domain rules (always-human / allow-login / overrides).\n"
                )

                tune = _prompt_choice("Also tune domain rules now?", ["y", "n"], "n")
                if tune == "y":
                    dom = _prompt("Domain to allow/override (e.g. forum.example or google.com)")
                    if dom:
                        # Allow-login
                        albp = _ensure_dict(cfg.get("allowed_login_domains_by_profile"))
                        cur = list(albp.get(profile) or [])
                        albp[profile] = _dedupe(cur + [dom])
                        cfg["allowed_login_domains_by_profile"] = albp
                        _save_json(cfg_path, cfg)
                        _write_config_receipt(
                            cfg_path,
                            "policy-wizard:allow-login",
                            {"profile": profile, "domain": dom},
                        )
                        sys.stdout.write(f"OK: allowed_login_domains_by_profile[{profile}] += {dom}\n")

                        # Optional override of always-human
                        ovq = _prompt_choice("Override always-human for this domain?", ["y", "n"], "n")
                        if ovq == "y":
                            ov = _ensure_dict(cfg.get("override_always_human_domains_by_profile"))
                            cur2 = list(ov.get(profile) or [])
                            ov[profile] = _dedupe(cur2 + [dom])
                            cfg["override_always_human_domains_by_profile"] = ov
                            _save_json(cfg_path, cfg)
                            _write_config_receipt(
                                cfg_path,
                                "policy-wizard:override-always-human",
                                {"profile": profile, "domain": dom},
                            )
                            sys.stdout.write(
                                f"OK: override_always_human_domains_by_profile[{profile}] += {dom}\n"
                            )
                    else:
                        sys.stdout.write("No domain entered; skipped domain tuning.\n")

                sys.stdout.write("Tip: you can also run 'governance domain-wizard' anytime.\n")
            changed.append((action, decision))

        if changed:
            sys.stdout.write("\nSummary:\n")
            for a, d in changed:
                sys.stdout.write(f"- {profile}.{a} = {d}\n")

        sys.stdout.write("\nTip: verify with:\n")
        sys.stdout.write("  governance decide --url <...> --action <...> --profile <...> --pretty --explain\n")
        return 0

    if args.cmd == "domain-wizard":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            cfg_path = DEFAULT_CONFIG_REL

        cfg = _load_config(cfg_path)
        if cfg is None:
            cfg = {}
        cfg = _ensure_dict(cfg)

        sys.stdout.write(f"Domain config: {cfg_path}\n")
        sys.stdout.write("Choose an operation.\n")

        while True:
            op = _prompt_choice(
                "Operation",
                [
                    "always-human add",
                    "always-human remove",
                    "allow-login add",
                    "allow-login remove",
                    "override-always-human add",
                    "override-always-human remove",
                    "show",
                    "(done)",
                ],
                "show",
            )
            if op == "(done)":
                break

            if op == "show":
                sys.stdout.write(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
                continue

            # shared inputs
            domain = _prompt("Domain (e.g. example.com or google.com)")
            if not domain:
                sys.stdout.write("No domain provided.\n")
                continue

            prof = None
            if op.startswith("allow-login") or op.startswith("override-always-human"):
                prof = _prompt_choice("Profile", ["strict", "standard", "experimental"], "experimental")

            if op.startswith("always-human"):
                cur = list(cfg.get("always_human_domains") or [])
                if op.endswith("add"):
                    cfg["always_human_domains"] = _dedupe(cur + [domain])
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"always_human_add": domain})
                    sys.stdout.write(f"OK: always_human_domains += {domain}\n")
                else:
                    cfg["always_human_domains"] = [x for x in cur if x != domain]
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"always_human_remove": domain})
                    sys.stdout.write(f"OK: always_human_domains -= {domain}\n")

            elif op.startswith("allow-login"):
                albp = _ensure_dict(cfg.get("allowed_login_domains_by_profile"))
                cur = list(albp.get(prof) or [])
                if op.endswith("add"):
                    albp[prof] = _dedupe(cur + [domain])
                    cfg["allowed_login_domains_by_profile"] = albp
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"allow_login_add": {prof: domain}})
                    sys.stdout.write(f"OK: allowed_login_domains_by_profile[{prof}] += {domain}\n")
                else:
                    albp[prof] = [x for x in cur if x != domain]
                    cfg["allowed_login_domains_by_profile"] = albp
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"allow_login_remove": {prof: domain}})
                    sys.stdout.write(f"OK: allowed_login_domains_by_profile[{prof}] -= {domain}\n")

            elif op.startswith("override-always-human"):
                ov = _ensure_dict(cfg.get("override_always_human_domains_by_profile"))
                cur = list(ov.get(prof) or [])
                if op.endswith("add"):
                    ov[prof] = _dedupe(cur + [domain])
                    cfg["override_always_human_domains_by_profile"] = ov
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"override_always_human_add": {prof: domain}})
                    sys.stdout.write(f"OK: override_always_human_domains_by_profile[{prof}] += {domain}\n")
                else:
                    ov[prof] = [x for x in cur if x != domain]
                    cfg["override_always_human_domains_by_profile"] = ov
                    _save_json(cfg_path, cfg)
                    _write_config_receipt(cfg_path, "domain-wizard", {"override_always_human_remove": {prof: domain}})
                    sys.stdout.write(f"OK: override_always_human_domains_by_profile[{prof}] -= {domain}\n")

        return 0

    if args.cmd == "wizard":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        policy_config = _load_config(cfg_path) if cfg_path else None

        mode = _prompt("Mode (strict|standard|experimental)", "experimental")
        action = _prompt(
            "Action (login|send-message|purchase|transfer-funds|upload|download|delete|db-delete|system-settings|tool-exec|read-secrets)",
            "login",
        )

        sys.stdout.write("Paste one URL per line. Empty line to run.\n")
        urls: list[str] = []
        while True:
            line = sys.stdin.readline()
            if line is None:
                break
            line = line.strip()
            if not line:
                break
            urls.append(line)

        if not urls:
            u = _prompt("URL")
            if u:
                urls = [u]

        for u in urls:
            # Use the same input builder as decide sugar would.
            policy_input = {
                "request_text": f"{action} @ {u}",
                "provenance": "USER_INTENT",
                "policy_profile": mode,
                "action": action,
                "effects": ACTION_EFFECTS.get(action, []),
                "targets": {"urls": [u]},
                "state": {"phase": "planning", "snapshot_ref": None},
            }
            out = decide(policy_input, policy_config=policy_config)
            sys.stdout.write("\n")
            sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
            sys.stdout.write(_explain(policy_input, out, policy_config) + "\n")

            if args.receipt_dir:
                from governance_runtime.version import __version__

                ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
                p = Path(args.receipt_dir)
                p.mkdir(parents=True, exist_ok=True)
                out_path = p / f"decision_{ts}.json"
                receipt = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "kind": "governance_runtime.receipt.v0",
                    "version": __version__,
                    "input": policy_input,
                    "output": out,
                }
                out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return 0

    if args.cmd == "decide":
        # If any sugar flags are present, build input from args. Otherwise require --in.
        using_sugar = any(
            [args.url, args.effects is not None, args.action, args.profile, args.provenance, args.request_text]
        )
        if using_sugar:
            policy_input = _build_input_from_args(args)
        else:
            if args.in_path is None:
                p_decide.error("either provide --in <path|-> or use sugar flags like --url/--effects")
            policy_input = _load_json(args.in_path)

        cfg_path = _resolve_config_path(args.config_path)
        policy_config = _load_config(cfg_path)
        out = decide(policy_input, policy_config=policy_config)

        if args.receipt_out:
            _write_receipt(args.receipt_out, policy_input, out)

        if args.pretty:
            json.dump(out, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        else:
            json.dump(out, sys.stdout)
            sys.stdout.write("\n")

        if args.explain:
            sys.stdout.write("\n" + _explain(policy_input, out, policy_config) + "\n")

        return 0

    if args.cmd == "demo":
        prof = (args.profile or "standard").strip().lower()
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        policy_config = _load_config(cfg_path) if cfg_path else None
        policy_config = policy_config or {}

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        receipt_dir = args.receipt_dir
        if not receipt_dir:
            receipt_dir = str(Path("runs") / f"demo_{ts}")
        out_dir = Path(receipt_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # For demo clarity, create an in-memory copy of config that allowlists a safe-ish demo domain.
        demo_cfg = json.loads(json.dumps(policy_config))
        albp = _ensure_dict(demo_cfg.get("allowed_login_domains_by_profile"))
        cur = list(albp.get(prof) or [])
        if "example.com" not in cur:
            cur.append("example.com")
        albp[prof] = cur
        demo_cfg["allowed_login_domains_by_profile"] = albp

        def _mk(name: str, inp: Dict[str, Any]) -> Dict[str, Any]:
            return {"name": name, "input": inp}

        scenarios = [
            _mk(
                "Safe read-only browse (no sharp effects → ALLOW)",
                {
                    "request_text": "open a public webpage and read it",
                    "provenance": "USER_INTENT",
                    "policy_profile": prof,
                    "action": None,
                    "effects": [],
                    "targets": {"urls": ["https://example.com/"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
            _mk(
                "Login to Google (always-human → DENY)",
                {
                    "request_text": "login to Gmail",
                    "provenance": "USER_INTENT",
                    "policy_profile": prof,
                    "action": "login",
                    "effects": ACTION_EFFECTS.get("login", []),
                    "targets": {"urls": ["https://mail.google.com/mail/u/0/#inbox"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
            _mk(
                "Login to example.com (allowlisted → ASK)",
                {
                    "request_text": "login to example.com",
                    "provenance": "USER_INTENT",
                    "policy_profile": prof,
                    "action": "login",
                    "effects": ACTION_EFFECTS.get("login", []),
                    "targets": {"urls": ["https://example.com/login"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
            _mk(
                "Purchase action (sharp money → policy-driven ASK/DENY)",
                {
                    "request_text": "buy a gift card",
                    "provenance": "USER_INTENT",
                    "policy_profile": prof,
                    "action": "purchase",
                    "effects": ACTION_EFFECTS.get("purchase", []),
                    "targets": {"urls": ["https://example.com/checkout"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
            _mk(
                "Delete action (destructive → ASK)",
                {
                    "request_text": "delete user account",
                    "provenance": "USER_INTENT",
                    "policy_profile": prof,
                    "action": "delete",
                    "effects": ACTION_EFFECTS.get("delete", []),
                    "targets": {"urls": ["https://example.com/settings"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
            _mk(
                "Tool-exec suggested by TOOL_OUTPUT (untrusted → DENY)",
                {
                    "request_text": "run rm -rf /",
                    "provenance": "TOOL_OUTPUT",
                    "policy_profile": prof,
                    "action": "tool-exec",
                    "effects": ACTION_EFFECTS.get("tool-exec", []),
                    "targets": {"tools": ["exec"]},
                    "state": {"phase": "planning", "snapshot_ref": None},
                },
            ),
        ]

        if args.extended:
            scenarios.extend(
                [
                    _mk(
                        "Upload action (privacy/export → ASK)",
                        {
                            "request_text": "upload a CSV to a website",
                            "provenance": "USER_INTENT",
                            "policy_profile": prof,
                            "action": "upload",
                            "effects": ACTION_EFFECTS.get("upload", []),
                            "targets": {"urls": ["https://example.com/upload"]},
                            "state": {"phase": "planning", "snapshot_ref": None},
                        },
                    ),
                    _mk(
                        "Download/install action (software → ASK)",
                        {
                            "request_text": "download and install an app",
                            "provenance": "USER_INTENT",
                            "policy_profile": prof,
                            "action": "download",
                            "effects": ACTION_EFFECTS.get("download", []),
                            "targets": {"urls": ["https://example.com/download"]},
                            "state": {"phase": "planning", "snapshot_ref": None},
                        },
                    ),
                    _mk(
                        "Commit point without state binding (requires snapshot → ASK)",
                        {
                            "request_text": "confirm a purchase",
                            "provenance": "USER_INTENT",
                            "policy_profile": prof,
                            "action": "purchase",
                            "effects": ACTION_EFFECTS.get("purchase", []),
                            "targets": {"urls": ["https://example.com/checkout"]},
                            "state": {"phase": "execution", "snapshot_ref": None},
                        },
                    ),
                    _mk(
                        "Read-secrets (crown-jewel class → DENY)",
                        {
                            "request_text": "read API keys from env",
                            "provenance": "USER_INTENT",
                            "policy_profile": prof,
                            "action": "read-secrets",
                            "effects": ACTION_EFFECTS.get("read-secrets", []),
                            "targets": {"tools": ["env"], "urls": []},
                            "state": {"phase": "planning", "snapshot_ref": None},
                        },
                    ),
                ]
            )

        if args.seed is not None:
            rng = random.Random(int(args.seed))
            n = max(0, int(args.count or 0))

            showcase_actions = [
                (None, [], "USER_INTENT"),
                ("login", ACTION_EFFECTS.get("login", []), "USER_INTENT"),
                ("purchase", ACTION_EFFECTS.get("purchase", []), "USER_INTENT"),
                ("delete", ACTION_EFFECTS.get("delete", []), "USER_INTENT"),
                ("upload", ACTION_EFFECTS.get("upload", []), "USER_INTENT"),
                ("download", ACTION_EFFECTS.get("download", []), "USER_INTENT"),
                ("tool-exec", ACTION_EFFECTS.get("tool-exec", []), "TOOL_OUTPUT"),
            ]

            metamorphic_families = [
                ("tool-exec", ACTION_EFFECTS.get("tool-exec", []), "TOOL_OUTPUT", "exec"),
                ("delete", ACTION_EFFECTS.get("delete", []), "USER_INTENT", None),
                ("purchase", ACTION_EFFECTS.get("purchase", []), "USER_INTENT", None),
            ]

            for j in range(n):
                if args.mode == "metamorphic":
                    action, effects, prov, tool = rng.choice(metamorphic_families)
                    verb = rng.choice(["please", "can you", "do this", "ASAP", "now", "carefully"])
                    req = f"{verb}: {action} request variation {j+1}".strip()
                    targets: Dict[str, Any] = {}
                    if tool:
                        targets["tools"] = [tool]
                    else:
                        targets["urls"] = [f"https://example.com/path/{j+1}"]
                    scenarios.append(
                        _mk(
                            f"Seeded metamorphic {j+1} ({action}, {prov})",
                            {
                                "request_text": req,
                                "provenance": prov,
                                "policy_profile": prof,
                                "action": action,
                                "effects": effects,
                                "targets": targets,
                                "state": {"phase": "planning", "snapshot_ref": None},
                            },
                        )
                    )
                else:
                    action, effects, prov = rng.choice(showcase_actions)
                    domain = rng.choice(
                        [
                            "example.com",
                            "shop.example.com",
                            "mail.google.com",
                            "accounts.google.com",
                            "files.example.com",
                        ]
                    )
                    path = rng.choice(["/", "/login", "/checkout", "/settings", "/upload", "/download"])
                    url = f"https://{domain}{path}"
                    req = rng.choice(
                        [
                            "open and read",
                            "please proceed",
                            "do the thing",
                            "help me with this",
                            "finish this step",
                        ]
                    )
                    targets: Dict[str, Any] = {"urls": [url]}
                    if action == "tool-exec":
                        targets = {"tools": ["exec"]}
                    scenarios.append(
                        _mk(
                            f"Seeded showcase {j+1} ({action or 'browse'}, {prov})",
                            {
                                "request_text": f"{req} (seeded {j+1})",
                                "provenance": prov,
                                "policy_profile": prof,
                                "action": action,
                                "effects": effects,
                                "targets": targets,
                                "state": {"phase": "planning", "snapshot_ref": None},
                            },
                        )
                    )

        sys.stdout.write("governance_runtime demo\n")
        sys.stdout.write(f"Profile: {prof}\n")
        if cfg_path:
            sys.stdout.write(f"Config: {cfg_path}\n")
        sys.stdout.write(f"Receipts: {out_dir}\n")

        # If not verbose, print a concise table-like output.
        if args.verbose:
            sys.stdout.write("\nScenarios:\n")
        else:
            sys.stdout.write("\n#  Name | Decision\n")

        counts = {"ALLOW": 0, "ASK": 0, "DENY": 0}
        reason_counts: Dict[str, int] = {}

        for i, sc in enumerate(scenarios, start=1):
            policy_input = sc["input"]
            out = decide(policy_input, policy_config=demo_cfg)
            decision = out.get("decision")
            counts[decision] = counts.get(decision, 0) + 1
            for r in list(out.get("reasons") or []):
                reason_counts[r] = reason_counts.get(r, 0) + 1

            if args.verbose:
                sys.stdout.write(f"\n{i}) {sc['name']}\n")
                sys.stdout.write(_explain(policy_input, out, demo_cfg) + "\n")
            else:
                sys.stdout.write(f"{i:>2}) {sc['name']} | {decision}\n")

            rec_path = out_dir / f"scenario_{i:02d}.json"
            _write_receipt(str(rec_path), policy_input, out)

        sys.stdout.write("\nSummary:\n")
        sys.stdout.write(f"- ALLOW: {counts.get('ALLOW', 0)}\n")
        sys.stdout.write(f"- ASK:   {counts.get('ASK', 0)}\n")
        sys.stdout.write(f"- DENY:  {counts.get('DENY', 0)}\n")

        # Top reasons (stable ids) are useful for quick sanity checks.
        if reason_counts:
            top = sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
            sys.stdout.write("\nTop reasons:\n")
            for rid, n in top:
                sys.stdout.write(f"- {rid}: {n}\n")

        sys.stdout.write("\nDone.\n")
        return 0

    if args.cmd == "doctor":
        from governance_runtime.version import __version__

        prof = (args.profile or "standard").strip().lower()
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        policy_config = _load_config(cfg_path) if cfg_path else None
        policy_config = policy_config or {}

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        receipt_dir = args.receipt_dir
        if not receipt_dir:
            receipt_dir = str(Path("runs") / f"doctor_{ts}")
        out_dir = Path(receipt_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        sys.stdout.write("governance doctor\n")
        sys.stdout.write(f"governance_runtime version: {__version__}\n")
        sys.stdout.write(f"python: {sys.version.splitlines()[0]}\n")
        sys.stdout.write(f"profile: {prof}\n")
        sys.stdout.write(f"config: {cfg_path or '(none found; using empty config)'}\n")
        sys.stdout.write(f"receipts: {out_dir}\n")

        # Quick check: run a seeded showcase demo and ensure we can write receipts.
        seed = int(args.seed)
        count = max(0, int(args.count))

        sys.stdout.write("\nRunning quick demo check...\n")
        demo_args = argparse.Namespace(
            cmd="demo",
            profile=prof,
            mode="showcase",
            extended=False,
            seed=seed,
            count=count,
            config_path=cfg_path,
            receipt_dir=str(out_dir),
        )

        # Reuse the demo implementation by calling the same code-path.
        # We do this by emulating the 'demo' handler logic below.
        # (Implementation lives inline, so we replicate the core bits.)
        demo_cfg = json.loads(json.dumps(policy_config))
        albp = _ensure_dict(demo_cfg.get("allowed_login_domains_by_profile"))
        cur = list(albp.get(prof) or [])
        if "example.com" not in cur:
            cur.append("example.com")
        albp[prof] = cur
        demo_cfg["allowed_login_domains_by_profile"] = albp

        # Minimal seeded scenarios only (plus base suite count indicator)
        base_inputs = [
            {
                "request_text": "open a public webpage and read it",
                "provenance": "USER_INTENT",
                "policy_profile": prof,
                "action": None,
                "effects": [],
                "targets": {"urls": ["https://example.com/"]},
                "state": {"phase": "planning", "snapshot_ref": None},
            }
        ]

        rng = random.Random(seed)
        showcase_actions = [
            (None, [], "USER_INTENT"),
            ("login", ACTION_EFFECTS.get("login", []), "USER_INTENT"),
            ("purchase", ACTION_EFFECTS.get("purchase", []), "USER_INTENT"),
            ("delete", ACTION_EFFECTS.get("delete", []), "USER_INTENT"),
            ("upload", ACTION_EFFECTS.get("upload", []), "USER_INTENT"),
            ("download", ACTION_EFFECTS.get("download", []), "USER_INTENT"),
            ("tool-exec", ACTION_EFFECTS.get("tool-exec", []), "TOOL_OUTPUT"),
        ]

        total = 0
        # Base check
        for inp in base_inputs:
            out = decide(inp, policy_config=demo_cfg)
            rec_path = out_dir / f"scenario_{total+1:02d}.json"
            _write_receipt(str(rec_path), inp, out)
            total += 1

        for j in range(count):
            action, effects, prov = rng.choice(showcase_actions)
            domain = rng.choice(["example.com", "shop.example.com", "mail.google.com", "accounts.google.com"])
            path = rng.choice(["/", "/login", "/checkout", "/settings", "/upload", "/download"])
            url = f"https://{domain}{path}"
            targets: Dict[str, Any] = {"urls": [url]}
            if action == "tool-exec":
                targets = {"tools": ["exec"]}
            inp = {
                "request_text": f"doctor check seeded {j+1}",
                "provenance": prov,
                "policy_profile": prof,
                "action": action,
                "effects": effects,
                "targets": targets,
                "state": {"phase": "planning", "snapshot_ref": None},
            }
            out = decide(inp, policy_config=demo_cfg)
            rec_path = out_dir / f"scenario_{total+1:02d}.json"
            _write_receipt(str(rec_path), inp, out)
            total += 1

        sys.stdout.write(f"OK: wrote {total} receipt(s)\n")
        sys.stdout.write("If you have issues, run: governance config-show && governance demo --seed 123 --count 5\n")
        return 0

    if args.cmd == "policy-show":
        prof = (args.profile or "experimental").strip().lower()
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        cfg = _load_config(cfg_path) if cfg_path else None
        cfg = cfg or {}

        # Read the merged effective action policies the same way the engine does.
        defaults = {
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

        merged = dict(defaults)
        apbp = cfg.get("action_policies_by_profile") or {}
        if isinstance(apbp, dict):
            for p2, rules in apbp.items():
                if not isinstance(rules, dict):
                    continue
                base = dict(merged.get(p2, {}))
                base.update(rules)
                merged[p2] = base

        table = merged.get(prof, {})
        sys.stdout.write(f"Profile: {prof}\n")
        if cfg_path:
            sys.stdout.write(f"Config: {cfg_path}\n")

        sys.stdout.write("\nAction policies:\n")
        for k in sorted(table.keys()):
            sys.stdout.write(f"- {k}: {table[k]}\n")

        sys.stdout.write("\nGuardrails:\n")
        sys.stdout.write("- strict/tight: read-secrets forced DENY\n")
        sys.stdout.write("- standard: read-secrets cannot be ALLOW (clamped to ASK)\n")
        return 0

    if args.cmd == "config-reset":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            cfg_path = DEFAULT_CONFIG_REL

        p = Path(cfg_path)
        if p.exists() and not args.force:
            sys.stdout.write(f"Config already exists: {cfg_path} (use --force to overwrite)\n")
            return 0

        default_cfg = {
            "always_human_domains": ["google.com", "appleid.apple.com"],
            "allowed_login_domains_by_profile": {"strict": [], "standard": [], "experimental": []},
            "override_always_human_domains_by_profile": {"standard": [], "experimental": []},
        }
        _save_json(cfg_path, default_cfg)
        _write_config_receipt(cfg_path, "config-reset", {"reset": True})
        sys.stdout.write(f"OK: reset config at {cfg_path}\n")
        return 0

    if args.cmd == "config-remove":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            p.error("no config path found; pass --config or run governance init")
        cfg = _load_config(cfg_path) or {}
        cfg = _ensure_dict(cfg)

        dom = args.domain
        field = args.field

        if field == "always-human":
            cur = [x for x in list(cfg.get("always_human_domains") or []) if x != dom]
            cfg["always_human_domains"] = cur
        elif field == "allow-login":
            if not args.profile:
                p_rm.error("--profile is required for --field allow-login")
            albp = _ensure_dict(cfg.get("allowed_login_domains_by_profile"))
            cur = [x for x in list(albp.get(args.profile) or []) if x != dom]
            albp[args.profile] = cur
            cfg["allowed_login_domains_by_profile"] = albp
        elif field == "override-always-human":
            if not args.profile:
                p_rm.error("--profile is required for --field override-always-human")
            ov = _ensure_dict(cfg.get("override_always_human_domains_by_profile"))
            cur = [x for x in list(ov.get(args.profile) or []) if x != dom]
            ov[args.profile] = cur
            cfg["override_always_human_domains_by_profile"] = ov

        _save_json(cfg_path, cfg)
        _write_config_receipt(cfg_path, "config-remove", {"field": field, "profile": args.profile, "domain": dom})
        sys.stdout.write(f"OK: removed {dom} from {field} (profile={args.profile or '-'}).\n")
        sys.stdout.write(f"Config: {cfg_path}\n")
        return 0

    if args.cmd == "config-show":
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            p.error("no config path found; pass --config or run governance init")
        cfg = _load_config(cfg_path)
        if cfg is None:
            p.error(f"could not load config at: {cfg_path}")
        sys.stdout.write(f"Config: {cfg_path}\n")
        sys.stdout.write(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
        sys.stdout.write("\nNotes:\n")
        sys.stdout.write("- Domain matching: exact + suffix (example.com matches a.example.com; *.example.com supported)\n")
        sys.stdout.write("- Defaults: profile=strict, provenance=USER_INTENT (unless you pass flags)\n")
        sys.stdout.write("- Tip: use 'governance decide --action <login|send-message|purchase|transfer-funds|upload|download|delete|db-delete|system-settings|tool-exec|read-secrets>'\n")
        return 0

    if args.cmd == "init":
        # Create local default config if it doesn't exist.
        cfg_path = _resolve_config_path(None)
        # If default config doesn't exist and env var isn't set, prefer local default path.
        if not cfg_path:
            cfg_path = DEFAULT_CONFIG_REL

        p = Path(cfg_path)
        if p.exists() and not args.force:
            sys.stdout.write(f"Config already exists: {cfg_path} (use --force to overwrite)\n")
            return 0

        default_cfg = {
            "always_human_domains": [
                "google.com",
                "appleid.apple.com",
            ],
            "allowed_login_domains_by_profile": {
                "strict": [],
                "standard": [],
                "experimental": [],
            },
            "override_always_human_domains_by_profile": {
                "standard": [],
                "experimental": [],
            },
            "action_policies_by_profile": {
                "strict": {
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
            },
        }
        _save_json(cfg_path, default_cfg)
        sys.stdout.write(f"OK: created config at {cfg_path}\n")
        sys.stdout.write("Next: try a quick decision:\n")
        sys.stdout.write(
            "  governance decide --url 'https://mail.google.com/' --action login --profile standard --pretty\n"
        )
        return 0

    if args.cmd in ("allow-login", "always-human", "override-always-human"):
        cfg_path = _resolve_config_path(getattr(args, "config_path", None))
        if not cfg_path:
            p.error("no config path found; pass --config or ensure ./config/policy_config_default_v0.json exists")

        cfg = _load_config(cfg_path) or {}
        cfg = _ensure_dict(cfg)

        if args.cmd == "always-human":
            cfg["always_human_domains"] = _dedupe(list(cfg.get("always_human_domains") or []) + [args.domain])

        elif args.cmd == "allow-login":
            albp = _ensure_dict(cfg.get("allowed_login_domains_by_profile"))
            cur = list(albp.get(args.profile) or [])
            albp[args.profile] = _dedupe(cur + [args.domain])
            cfg["allowed_login_domains_by_profile"] = albp

        elif args.cmd == "override-always-human":
            ov = _ensure_dict(cfg.get("override_always_human_domains_by_profile"))
            cur = list(ov.get(args.profile) or [])
            ov[args.profile] = _dedupe(cur + [args.domain])
            cfg["override_always_human_domains_by_profile"] = ov

        _save_json(cfg_path, cfg)

        # Print a minimal summary of what changed (public-friendly) + write a config-change receipt.
        if args.cmd == "always-human":
            change = {"always_human_domains_add": args.domain}
            _write_config_receipt(cfg_path, args.cmd, change)
            sys.stdout.write(f"OK: always_human_domains += {args.domain}\n")
            sys.stdout.write(f"Config: {cfg_path}\n")
        elif args.cmd == "allow-login":
            change = {"allowed_login_domains_add": {args.profile: args.domain}}
            _write_config_receipt(cfg_path, args.cmd, change)
            sys.stdout.write(f"OK: allowed_login_domains_by_profile[{args.profile}] += {args.domain}\n")
            sys.stdout.write(f"Config: {cfg_path}\n")
        elif args.cmd == "override-always-human":
            change = {"override_always_human_domains_add": {args.profile: args.domain}}
            _write_config_receipt(cfg_path, args.cmd, change)
            sys.stdout.write(
                f"OK: override_always_human_domains_by_profile[{args.profile}] += {args.domain}\n"
            )
            sys.stdout.write(f"Config: {cfg_path}\n")
        else:
            _write_config_receipt(cfg_path, args.cmd, {"updated": True})
            sys.stdout.write(f"OK: updated {cfg_path}\n")

        return 0

        if args.receipt_out:
            _write_receipt(args.receipt_out, policy_input, out)

        if args.pretty:
            json.dump(out, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        else:
            json.dump(out, sys.stdout)
            sys.stdout.write("\n")
        return 0

    p.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
