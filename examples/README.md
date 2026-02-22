# Examples

These examples are meant to be copy/paste runnable.

From the project root:

```bash
source .venv/bin/activate
```

## 1) Money (purchase) -> ASK
```bash
governance decide --in examples/example_input_money.json --pretty
```

## 2) Login via action (derived effects)
```bash
governance decide --url "https://mail.google.com/mail/u/0/#inbox" --action login --profile standard --pretty
```

## 3) Login allowlist (DENY → ASK)
This shows a concrete before/after:

```bash
# default behavior: logins are denied unless allowlisted
(governance decide --url "https://reddit.com/login" --action login --profile standard --pretty --explain) || true

# allowlist the domain for the profile (login becomes ASK)
governance allow-login --profile standard --domain reddit.com

governance decide --url "https://reddit.com/login" --action login --profile standard --pretty --explain

# optional: remove it again (back to default)
governance config-remove --field allow-login --profile standard --domain reddit.com
```

## 4) Always-human (suffix matching)
```bash
governance always-human --domain google.com

governance decide --url "https://mail.google.com/" --action login --profile standard --pretty --explain
```

## 5) Always-human override (DENY → ASK)
This demonstrates how `override-always-human` can change a non-delegable domain into an allowlistable one (still ASK, not ALLOW).

```bash
# mark as always-human
governance always-human --domain reddit.com

# login is now DENY
governance decide --url "https://reddit.com/login" --action login --profile standard --pretty --explain

# override always-human for this profile
governance override-always-human --profile standard --domain reddit.com

# now allowlist login
governance allow-login --profile standard --domain reddit.com

# login becomes ASK
governance decide --url "https://reddit.com/login" --action login --profile standard --pretty --explain

# cleanup (optional)
governance config-remove --field allow-login --profile standard --domain reddit.com
```

## 6) Toy PEP wrapper demo (PDP called before a tool call)
This is a tiny illustration of how a policy enforcement point (PEP) could call the policy decision point (PDP) before running a tool.

```bash
python examples/pep_wrapper_demo.py
```
