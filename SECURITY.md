# Security policy (MVP)

This is an MVP governance tool intended for local use and experimentation.

## Non-goals (current)
- This project is not a hardened production security boundary.
- It does not automatically intercept every tool call in a running agent.

## Reporting
If you find a security issue or a design flaw that could cause unsafe behavior:
- Please report privately (DM/email) and include reproduction steps.

## Design stance
- Defaults are conservative.
- Sharp edges should route to ASK/DENY.
- Changes should be test-backed (pytest + metamorphic/variation tests).

## Threat categories
This project describes threats in plain language (prompt injection, data exposure, over-privileged actions).
It does not claim compliance with any external standard.
