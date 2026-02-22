# governance_runtime (MVP)

A small, deterministic **policy gate** for tool-using agents.

Given a request + provenance + effect tags (money/privacy/reputation/etc.) + targets (URLs/domains), it returns:
- **ALLOW** (safe to proceed)
- **ASK** (requires bounded human approval; TTL + scope + optional state binding)
- **DENY** (non-delegable by default)

It also supports **receipts** (audit artifacts) and a growing **pytest** suite (quizzes + metamorphic/variation tests) to prevent safety regressions.


## Why this exists
LLM agents fail in two common ways:

1) **Action-level risk:** untrusted content smuggles instructions that lead to irreversible actions.
2) **Judgment-level risk:** persuasive framing (priming/salience) biases decisions.

This project focuses on **action-level governance**: keep sharp actions behind explicit gates, and make the decision procedure testable.

## Conceptual model (PDP/PEP)
In access-control terminology:
- `governance decide` is a **PDP** (Policy Decision Point): it returns ALLOW/ASK/DENY.
- Your agent/tool wrapper is a **PEP** (Policy Enforcement Point): it asks the PDP, then enforces the decision.

This repo intentionally ships only the PDP.


## Threat model (MVP)
This MVP is designed to reduce risk from:
- prompt/tool-output injection (untrusted content smuggling instructions)
- over-privileged actions (doing sharp actions without explicit approval)
- approval replay (stale approvals; default TTL 5 minutes)

It does **not** (yet) solve:
- automatically deriving effect tags from arbitrary tool plans
- full browser/tool integration (enforcement is still manual/simulated)


## Quick demo (proof-on-demand)
Fast path: run `governance demo`. Everything else below is optional.

```bash
cd governance_runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q

governance demo

# bigger fixed suite
governance demo --extended

# seeded, deterministic variations (same output for the same seed)
governance demo --seed 123 --count 50

# metamorphic mode (wording variations intended not to change decisions)
governance demo --mode metamorphic --seed 123 --count 50

# verbose output (prints detailed 'Why' per scenario)
governance demo --seed 123 --count 10 --verbose

# sharing evidence (optional): save console output while receipts are written
# (useful if someone asks you to DM what you saw)
governance demo --seed 123 --count 50 | tee demo_output.txt
```

Or run a single decision:
```bash
governance decide --url "https://mail.google.com/mail/u/0/#inbox" \
  --action login \
  --profile standard \
  --pretty --explain
```

## Install / Quickstart
Notes:
- Runtime has **no external dependencies** (Python standard library only).
- Tests use `pytest` (installed via `.[dev]`).

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate

pip install -e '.[dev]'
pytest -q
```

### Uninstall / remove
If you used a virtualenv (recommended), removal is simple:
- deactivate and delete the `.venv/` folder, or
- run:

```bash
pip uninstall governance_runtime
```

Tip: create a default config file in ./config/:
```bash
governance init
```


## CLI usage (JSON input)
```bash
python -m governance_runtime decide --in input.json --pretty \
  --config config/policy_config_default_v0.json \
  --receipt-out runs/receipt_1.json
```


## CLI usage (simple; recommended)
Use `--action` so effects are derived automatically:

```bash
governance decide \
  --url "https://mail.google.com/mail/u/0/#inbox" \
  --action login \
  --profile standard \
  --pretty
```

## CLI usage (advanced)
If needed, you can specify effect tags directly:

```bash
governance decide \
  --url "https://mail.google.com/mail/u/0/#inbox" \
  --effects LOGIN CREDENTIALS \
  --profile standard \
  --config config/policy_config_default_v0.json \
  --pretty \
  --receipt-out receipts/receipt_gmail.json
```


## What works right now (MVP scope)
- Deterministic decision: **ALLOW / ASK / DENY**
- CLI supports **URL paste** + **simple actions** (`--action` derives effects)
  - includes `read-secrets` which is DENY by default
  - includes `system-settings`, `db-delete`, `transfer-funds` (conservative defaults)
- Config supports:
  - always-human domains (non-delegable by default)
  - per-profile allowlisted login domains (LOGIN/CREDENTIALS becomes ASK)
  - per-profile overrides for always-human domains
- Domain matching: exact + suffix (e.g. `google.com` matches `mail.google.com`)
- Receipts: `--receipt-out <path>` writes an audit JSON including tool version
- Tests: run `pytest -q`

## What does NOT exist yet
- Automatic effects derivation from arbitrary tool plans (beyond `--action` presets)
- A full enforcement layer that intercepts every real tool call automatically

## Tiny PEP integration demo (example)
There is a minimal example wrapper showing how a PEP might call the PDP before executing a tool call:
- `examples/pep_wrapper_demo.py`

This is intentionally a toy example (no real tools are executed).

## Policy config (domains)
The config file controls:
- `always_human_domains`: domains that are non-delegable by default (e.g., Google/Apple).
- `allowed_login_domains_by_profile`: per-profile allowlist for site-native logins (LOGIN/CREDENTIALS becomes **ASK**).
- `override_always_human_domains_by_profile`: per-profile overrides that remove a domain from `always_human_domains`.

Domain matching supports suffix rules:
- `google.com` matches `mail.google.com`, `accounts.google.com`, etc.
- `*.google.com` and `.google.com` are also supported.

Default config:
- `config/policy_config_default_v0.json`


## Receipts
Use `--receipt-out` to write a JSON artifact containing:
- timestamp
- version
- input
- output

This is intended for auditing, debugging, and (optionally) sharing evidence of behavior.

### Future: tamper-evident receipt chains
A common hardening step for audit logs is a **hash-chained** format (each receipt includes the hash of the previous receipt) to make deletion/reordering detectable.

This is not implemented in the MVP yet; it’s a planned upgrade.

## Troubleshooting
See `TROUBLESHOOTING.md`.

## License / Security
- License: `LICENSE`
- Security notes: `SECURITY.md`
- Disclaimer: `DISCLAIMER.md`
- Changes: `CHANGELOG.md`


## DM run script
- `DM_SCRIPT.md` — copy/paste instructions you can DM to someone so they can run the demo themselves.
- `NOTES/SHARING_CLEAN.md` — notes on keeping a share folder clean (running in-place creates normal Python artifacts).

## Wizards (no-JSON UX)
- `governance wizard` — run decisions on many URLs interactively.
- `governance policy-wizard` — tune action decisions (ALLOW/ASK/DENY) interactively. For `login`, it can optionally help you update domain allowlists in the same flow.
- `governance domain-wizard` — tune always-human / allow-login / overrides interactively.

## Project structure
- `spec/` — human-readable specs (effects taxonomy, policy contract, approval token schema)
- `governance_runtime/` — Python package
  - `policy/decide.py` — the deterministic policy engine
  - `cli.py` — CLI wrapper
- `tests/` — pytest regression suite
- `config/` — default policy config
- `runs/` — optional receipts


## Related work / conceptual analogs (optional reading)
These are not dependencies; they’re useful for positioning and future integration ideas:
- **OPA (Open Policy Agent)** / Rego (policy-as-code): https://www.openpolicyagent.org/docs/
- **AWS Cedar** (authorization policy language): https://www.cedarpolicy.com/

## Next steps (planned)
- Expand quiz coverage + more metamorphic/variation tests.
- Add an effects-derivation layer for common actions.
- (Optional) add a policy-language backend (OPA/Rego or Cedar) behind the same decision contract.
- (Later) integrate as an enforcement layer (PEP) in front of real tool actions.
