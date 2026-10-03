# Codex manifest

ChatGPT base checkpoint: v001
Updated: 2026-10-03

## Imported base

The extracted checkpoint matched all 46 checksum entries. A standalone Git repository preserves that verified base as `643ba04`. ChatGPT's manifest is unchanged. Native 0.1.0 work is recorded in commit `1ef490f` and the archived verification/audit evidence.

## Local changes

- Native Windows Unix-domain socket transport, verified Desktop provenance and exact-thread separate-writer queue handling remain in the recovery engine.
- Discovery uses the user-selected 24-hour failed-turn completion window; durable obligations survive that window.
- Version 0.2.0 adds a native Windows tray and portable GUI/console EXEs, using pystray and Pillow rather than custom UI infrastructure.
- Tray and CLI share start/stop/restart/scan, status, settings, prompt, telemetry, initialization, scope and login controls.
- Continuation text lives in an associated-editor Markdown file and is re-read immediately before each send.
- Default scope covers interactive CLI, VS Code and Desktop; executor and sub-agent sessions remain excluded.
- Shared per-user locks prevent multiple app folders from dispatching simultaneously while portable data stays beside the EXEs.
- Metadata-only local JSONL telemetry defaults to keyed private identifiers; detailed mode retains actual IDs, names and paths without bodies or credentials.
- Submitted-delivery observations survive restart and record later turn metadata without claiming guaranteed causal attribution.
- Clean builds include MIT licensing, original dependency notices, matching LGPL tray source, per-file hashes and no runtime data.
- Public documentation contains a dated, primary-source comparison of 12 related projects/services, with explicit client and protocol limits.
- The App deployment is enabled at per-user Windows login, with detailed 64 MiB/16-backup logs and the existing prompt preserved.
- Version 0.2.1 fixes native popup lifetime: each menu is built on the UI thread at right-click and remains intact while tracked; background updates cannot destroy hover state.
- The installed Python package is upgraded to 0.2.1 and its CLI controls the registered portable copy.
- Previous per-user empty state, config and logs remain untouched; historical native verification and audits remain indexed.

## Verification

Native Windows 11 build 10.0.26300, PowerShell 7.6.6, Python 3.13.7, Codex CLI/daemon 0.160.0:

- Final native gate: 134 passed, no skips, 24.59s; compileall and 0.2.1 version smoke passed.
- Two native popup regressions preserve real MFS_HILITE state during background/callback updates and verify fresh labels, checkmarks and enabled states on reopening. Tracking/focus are intercepted; no visual mouse-hover check is claimed.
- 0.2.1 native UI-loop startup/shutdown passed without opening a popup. Frozen activation emitted tray.ready for 0.2.1 and a live monitoring cycle with 3 scanned, zero detected/dispatched/pending.
- The deployed update preserved all 6 existing data files byte-for-byte before launch; a recoverable previous App folder remains in ignored local staging. All 522 staged release files were verified, including the frozen Win32 adapter.
- Native shortcut tests passed with both PowerShell 7 and built-in Windows PowerShell, including Unicode/spaces/percent paths.
- Real Win32 tray/menu probe: 21 menu entries; start, immediate scan, stop, one cycle and quit passed.
- Real read-only interactive CLI probe: verified separate writer, acknowledged exact queue ID and completed queued turn; owned chat archived and process stopped.
- Frozen release probe passed spaces/percent paths, local data, exclusive instance protection, scan, settings restart, private/detailed logs and graceful stop.
- Managed GUI shortcut launch produced tray.ready and a live monitoring snapshot: 3 recent chats, zero detected/dispatched/pending.
- Installed CLI status resolved App/data and confirmed running, allInteractive, detailed logging and startup enabled.
- Natural quota-reset automatic delivery, actual VS Code extension UI delivery, 2 simultaneous real quota failures and a fresh Windows login were not observed.
- Exact settings, source provenance and remaining limits are in Docs/VALIDATION.md and the current dated audit.

## Artifacts

Shareable portable ZIP: `dist/codex-auto-continuer-0.2.1-windows-x86_64.zip`.
Optional wheel: `dist/codex_auto_continuer-0.2.1-py3-none-any.whl`.
Stable source transport: `codex-auto-continuer-codex-handoff.zip`.

The handoff includes source, tests, docs, helpers and audit state with hashes and Git provenance. It excludes App, local runtime data, installed dependencies, build output and secrets. Packaging runs audit retention and transport validation.
