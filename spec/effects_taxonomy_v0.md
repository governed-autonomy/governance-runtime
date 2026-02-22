# Effects taxonomy (v0)

Purpose: canonical effect tags for **gate-by-effect** decisions.

## Core tags (sharp-edge groups)

### [MONEY]
Definition: any action that could directly change financial position.
Examples:
- placing/canceling/modifying orders
- sending funds/crypto, signing transactions
- purchasing/subscribing
- entering payment details

### [PRIVACY]
Definition: any action that could expose or move personal/private data.
Examples:
- uploading/exporting files
- sending screenshots/logs externally
- sharing personal identifiers, addresses, account info

### [REPUTATION]
Definition: any action that creates a public or semi-public footprint.
Examples:
- social posts (X/LinkedIn), DMs, account settings changes
- publishing under your name/brand

## Operational effect tags

### CREDENTIALS
Definition: touching secrets, passwords, API keys, tokens, or 2FA.
Default: ASK/DENY depending on context; never accept untrusted approval.

### LOGIN
Definition: authentication flows (including account creation).
Notes:
- Primary identity providers (Google/Apple/primary email/password managers) are **always-human by default**.

### EXTERNAL_COMMS
Definition: sending messages/email/DMs to other humans/systems.
Notes:
- includes “send”, “reply”, “post”, “comment”, “DM”.

### DOWNLOAD_INSTALL
Definition: downloading files, installing software, running untrusted binaries.

### FILE_WRITE
Definition: creating/modifying local files (non-destructive).
Notes:
- within workspace is usually allowed; outside workspace may be ASK.

### DELETE_DESTRUCTIVE
Definition: deletions, overwrites without backup, irreversible edits.
Default: ASK.

### EXPORT_UPLOAD
Definition: moving data out (upload/export/share).
Default: ASK.

### BROWSER_COMMIT_POINT
Definition: last irreversible click/submit in a UI flow.
Default: ASK with snapshot/state binding.

### TOOL_EXECUTION
Definition: executing an external side-effecting tool call (network, state change).
Default: route through policy decision.

## Provenance tags (input source)
These are not “effects” but are required for decisions.
- USER_INTENT (trusted user in this chat)
- UNTRUSTED_CONTEXT (web/email/docs/tool output text)
- TOOL_OUTPUT (results from tools; still not an instruction)
