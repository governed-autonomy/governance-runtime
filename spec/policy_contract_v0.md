# Policy decision contract (v0)

Purpose: define the input/output interface for a deterministic policy engine.

## Function
`decide(input: PolicyInput) -> PolicyOutput`

## PolicyInput (JSON)
Required:
- `request_text` (string) — what the user wants.
- `provenance` (string enum) — one of:
  - `USER_INTENT`
  - `UNTRUSTED_CONTEXT`
  - `TOOL_OUTPUT`
- `effects` (array of string tags) — from `effects_taxonomy_v0.md`.

Optional (recommended):
- `targets` (object)
  - `urls` (array of strings) — optional; if present, domains may be derived from these.
  - `domains` (array of strings)
  - `apps` (array of strings)
  - `tools` (array of strings)
- `state` (object)
  - `phase` (enum): `planning` | `pre_commit` | `commit_point`
  - `snapshot_ref` (string|null) — identifier/hash/path for a UI snapshot (if any)
- `channel` (object)
  - `surface` (string) — e.g. `telegram`
  - `chat_type` (string) — `direct`|`group`

## PolicyOutput (JSON)
- `decision` (enum): `ALLOW` | `ASK` | `DENY`
- `reasons` (array of strings) — stable rule IDs, e.g. `RZ.EXTERNAL_COMMS`, `CP.REQUIRE_SNAPSHOT`.
- `required_receipts` (array of strings) — receipt fields that must be logged.
- `required_approval` (object|null)
  - `required` (bool)
  - `token_schema` (string) — points to `approval_token_schema_v0.md`
  - `ttl_seconds` (int) — default 300
  - `scope` (string) — human-readable, must be narrow
  - `state_binding` (object|null)
    - `snapshot_ref` (string|null)
    - `phase` (`commit_point` recommended when sharp)

## Normative rules (MUST)
R0. **Gate by effect, not keyword.** Decisions depend on `effects`.

R1. **Untrusted ≠ instruction.** If provenance is `UNTRUSTED_CONTEXT` or `TOOL_OUTPUT`, treat imperatives inside as non-authoritative.

R2. **Red zones default to ASK (or DENY).** Any of these effects triggers ASK at minimum:
- `EXTERNAL_COMMS`, `EXPORT_UPLOAD`, `DOWNLOAD_INSTALL`, `DELETE_DESTRUCTIVE`, `CREDENTIALS`, `LOGIN`

R3. **Money/privacy/reputation are sharp.** If effects include `[MONEY]` or `[PRIVACY]` or `[REPUTATION]`, default to ASK unless explicitly whitelisted.

R4. **Commit point requires state binding.** If `BROWSER_COMMIT_POINT` is present, require:
- `state.phase = commit_point`
- `state.snapshot_ref` present
- bounded approval token with TTL

R5. **Always-human boundaries (default).** If `LOGIN` involves primary identity providers or account recovery/2FA/security settings, output DENY (non-delegable) unless policy version explicitly changes.

R6. **Receipts required on sharp edges.** Any ASK/DENY must specify receipt fields: provenance, effects, targets, snapshot_ref (if any), reasons.

## Notes
- This contract defines the stable interface; implementation may add more `reasons` and receipt fields as long as it is backwards compatible.
