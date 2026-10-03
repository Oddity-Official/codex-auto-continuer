# Codex manifest

ChatGPT base checkpoint: v001
Updated: 2026-10-03

## Imported base

The existing extracted checkpoint matched all 46 entries in its checksum manifest. No replacement import was needed. Created a standalone Git repository and committed that verified base as `643ba04`. ChatGPT's manifest is preserved.

## Local work

- Added native Windows Unix-domain socket address marshalling without third-party runtime dependencies.
- Corrected Desktop discovery using the verified vscode/Codex Desktop originator pair.
- Added exact-thread separate-app-server writer handling through the verified shared queue.
- Set the user-selected 24-hour failure-completion discovery window; recorded obligations remain durable beyond it.
- Removed unsafe timestamp-only discovery caching and revalidated quota plus exact thread/turn after resume.
- Required stale queue deletion confirmation and deterministic durable client IDs.
- Acquired the instance lock before loading state; synced state writes before replacement.
- Bounded total RPC duration, cleaned initialization failures and bounded Codex subprocesses without console windows.
- Added hidden native Startup shortcut, background start, graceful stop, running status and rotating privacy-safe logs.
- Added regressions for confirmed failures and native shortcut/socket/locking integration.
- Preserved original v001 research and validation under Docs/History and reconciled current owner documents.
- Installed version 0.1.0, created the per-user config and login shortcut, and left the supervisor running as requested.

## Verification

Native Windows 11 build 10.0.26300, PowerShell 7.6.6, Python 3.13.7, Codex CLI/daemon 0.160.0:

- Native gate: 119 passed, no skips; compileall and version smoke passed.
- Native wheel build/install and installed command discovery passed.
- Final wheel matches all 13 runtime modules; package metadata, Markdown file targets and diff whitespace checks passed.
- Live read-only daemon probe passed.
- Separate-owner queue delivery, unloaded queue CRUD, exact deletion and detached queued-turn completion passed on owned test threads.
- Isolated native HTTP quota fixture persisted failed/usageLimitExceeded with completedAt; no real account request or quota exhaustion.
- Installed instance exclusion, idempotent start and graceful stop checks passed.
- Generated login shortcut launched successfully; background status verified.
- Production runtime observed a real quota failure in this chat, waited through 9 unavailable-usage scans, then cancelled the stale obligation after manual resume with zero duplicate dispatches.
- Automatic continuation at natural recovery, two simultaneous real quota failures and a fresh Windows login were not observed. Exact limits are recorded in Docs/VALIDATION.md.

Stable source transport: `codex-auto-continuer-codex-handoff.zip`. Release wheel: `dist/codex_auto_continuer-0.1.0-py3-none-any.whl`. Audit retention and per-file transport validation run during handoff packaging.
