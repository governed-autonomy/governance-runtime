# Troubleshooting

## `governance: command not found`
You likely forgot to activate the virtual environment.

```bash
cd governance_runtime
source .venv/bin/activate
which governance
```

If you still don't see it, reinstall editable:
```bash
pip install -e .
```

## `no config path found`
Create a default config:
```bash
governance init
```

Or pass a config explicitly:
```bash
governance decide --config config/policy_config_default_v0.json ...
```

## I changed config but decisions didn't change
Check which config file is actually being used:
```bash
governance config-show
```

## How to undo a config mistake
Reset config to defaults:
```bash
governance config-reset --force
```

Remove one entry:
```bash
governance config-remove --field always-human --domain google.com
```
