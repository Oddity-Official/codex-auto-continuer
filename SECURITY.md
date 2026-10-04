# Security and safe reporting

CAC is an independent local tool using experimental Codex interfaces. It has no remote analytics or log upload. The [signed updater](Docs/UPDATES.md) requests GitHub releases without sending chat data. Optional private-repository authentication uses an existing GitHub CLI token only in memory, never in logs or release assets. Codex credentials, conversation bodies and prompt text are not collected. Codex's network behavior is separate.

## Share diagnostics safely

- Include CAC and Codex versions, Windows version, the command or menu action, expected behavior and a minimal reproduction with synthetic chats where possible.
- Inspect a small relevant log excerpt before attaching it. Detailed logs contain real chat names, IDs and filesystem paths. Switching to Private does not rewrite older logs.
- Private logs use stable keyed identifiers, not guaranteed anonymous data. Durable `state.json` contains real IDs; settings and the Markdown prompt are user-authored. Never attach a whole used data folder or its correlation key.
- Do not attach Codex authentication files, session files, raw RPC payloads, screenshots of private conversations or your entire deployed app folder.

Logs and state are not encrypted. Private logging is the release default; Detailed logging is a deliberate local debugging choice.

## Report a vulnerability

If the repository's Security tab offers `Report a vulnerability`, use that private channel. Otherwise, open a minimal issue requesting a private contact method before sending sensitive details. Do not put credentials or private conversations in a public issue. Revoke a leaked credential immediately; deleting a post or file is not sufficient.

Recovery intentionally stops on protocol drift and ambiguous sends. Queue operations have no verified atomic turn precondition or idempotency guarantee. Do not delete pending state to force a retry or disable these checks to bypass an error. [Architecture](Docs/ARCHITECTURE.md) and [verification limits](Docs/VALIDATION.md#remaining-limits) describe the boundary.
