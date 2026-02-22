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

## 3) Allowlist a domain for login (standard)
```bash
governance allow-login --profile standard --domain forum.example

governance decide --url "forum.example/login" --action login --profile standard --pretty
```

## 4) Always-human (suffix matching)
```bash
governance always-human --domain google.com

governance decide --url "https://mail.google.com/" --action login --profile standard --pretty
```

