# Keeping the DM packet clean

Running the project in-place will create local artifacts (normal for Python projects), such as:
- `.venv/`
- `.pytest_cache/`
- `governance_runtime.egg-info/`
- `runs/` (demo/doctor receipts)
- `demo_output.txt` (if you use `tee`)

## Recommended workflow
If you want to share a clean folder, do one of these:

### Option A (best): run in a copy
Copy the packet to a temp folder and run there:

```bash
cp -R governance_runtime_dm_packet_v0_2026-02-21 /tmp/gr_packet
cd /tmp/gr_packet/governance_runtime
# run venv/tests/demo here
```

### Option B: re-generate the packet from the main repo
The OpenClaw workspace can regenerate a clean packet at any time.

## If you already ran it and want to clean manually
Delete these (safe to delete; they’re generated artifacts):
- `.venv/`
- `.pytest_cache/`
- `governance_runtime.egg-info/`
- `runs/`
- `demo_output.txt`
- `__pycache__/` and `*.pyc`
