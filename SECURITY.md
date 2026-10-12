# Security and safe reporting

CAC is an independent local tool using experimental Codex interfaces. It has no remote analytics or log upload. The [signed updater](Docs/UPDATES.md) requests GitHub releases without sending chat data. Optional private-repository authentication uses an existing GitHub CLI token only in memory, never in logs or release assets. Conversation bodies, prompt text and credentials never enter telemetry. Codex's network behavior is separate.

Optional queue holding is off by default. It stores canonical held input and embedded attachments in `held-inputs.dpapi`, encrypted for the Windows account and bound to the native Codex home/account. It does not archive conversations. Native authentication metadata is read only to establish the account binding; tokens are never retained or logged. Windows account encryption does not protect against software/admins able to act as that account. Keep used journals private; explicit input review reveals bodies only to the local user. [The user guide](Docs/USER-GUIDE.md#optional-queue-holding) explains coverage and manual-resolution risks.

## Share diagnostics safely

- Include CAC and Codex versions, Windows version, the command or menu action, expected behavior and a minimal reproduction with synthetic chats where possible.
- Inspect a small relevant log excerpt before attaching it. Detailed logs contain real chat names, IDs and filesystem paths. Switching to Private does not rewrite older logs.
- Private logs use stable keyed identifiers, not guaranteed anonymous data. Durable `state.json` contains real IDs; settings and the Markdown prompt are user-authored. Never attach a whole used data folder or its correlation key.
- Do not attach Codex authentication files, session files, raw RPC payloads, screenshots of private conversations or your entire deployed app folder.
- Do not attach `held-inputs.dpapi`, even encrypted. Never force recovery by deleting it. The journal and its plaintext bodies are excluded from clean releases and source handoffs.

Logs and state are not encrypted. Private logging is the release default; Detailed logging is a deliberate local debugging choice.

## Report a vulnerability

Use [private vulnerability reporting](https://github.com/Oddity-Official/codex-auto-continuer/security/advisories/new) for security issues. Do not put credentials or private conversations in a public issue. Revoke a leaked credential immediately; deleting a post or file is not sufficient.

Recovery blocks writes on protocol or identity drift. An unresolved ambiguous send quarantines its chat while other safe chats continue; CAC never blindly retries it. Queue operations have no verified atomic turn precondition or idempotency guarantee. Do not delete pending state to force a retry or disable these checks to bypass an error. [Architecture](Docs/ARCHITECTURE.md) and [verification limits](Docs/VALIDATION.md#environment-and-limits) describe the boundary.
