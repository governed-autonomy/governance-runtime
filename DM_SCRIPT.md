# DM run script (copy/paste)

If you want someone to run this locally (macOS/Linux), you can send them this.

---

## 60-second run

Notes:
- Runtime has **no external dependencies** (Python standard library only).
- Tests use `pytest` (installed via `.[dev]`).

```bash
# 1) enter repo
cd governance_runtime

# 2) create + activate venv
python3 -m venv .venv
source .venv/bin/activate

# 3) install + run tests
pip install -e '.[dev]'
pytest -q

# 4) proof-on-demand demo (writes receipts)
governance demo --seed 123 --count 50
```

## If something fails

```bash
# quick environment self-check
governance doctor

# show the resolved config
governance config-show
```

## Tweaking rules without editing JSON

```bash
# tune action decisions
governance policy-wizard

# tune domains (always-human / allow-login / overrides)
governance domain-wizard

# view effective action policy table
governance policy-show --profile experimental
```
