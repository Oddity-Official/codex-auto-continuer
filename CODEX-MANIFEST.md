# Codex manifest

ChatGPT base checkpoint: v001

Updated: 2026-10-03

## Imported base

The extracted checkpoint matched all 46 checksum entries. A standalone Git repository preserves the verified base as `643ba04`. ChatGPT's manifest is unchanged. Earlier native work and verification remain in Git and indexed historical evidence.

## Local changes

- Application version 0.3.0, with independent VS Code, CLI and Desktop choices; executor and sub-agent jobs remain excluded.
- Native Windows socket transport, exact-thread separate-writer handling, quota-only authority, 24-hour failed-turn discovery, durable obligations, stale queue cancellation and conservative ambiguous-send behavior remain intact.
- Annotated TOML overrides use built-in defaults when absent and preserve comments on tray edits. Valid saved changes apply at cycle boundaries; invalid settings or prompts pause dispatch without losing state and recover after repair.
- The default saved Markdown prompt is Continue. Existing user text is preserved and re-read before every send.
- The tray contains everyday controls only. Diagnostic scan/once/restart/init remain in the CLI; scan now acknowledges its exact completed request and returns actual counts.
- About/status/privacy/reset dialogs have independent owned native UI threads; the tray's popup and monitor worker remain responsive.
- Settings/prompt/folder actions run directly and asynchronously, independent of the control queue and companion EXE startup.
- Private/Detailed remains a privacy choice. Compact logging records cycle/RPC aggregates, changed metadata and explicit critical recovery events; optional trace enables allowlisted RPC summaries.
- Rotation defaults to 8 MiB plus three compressed backups per stream. Nested excluded sub-agent payloads are not copied into telemetry.
- A project-owned lossless SVG renders the green/yellow/red runtime assets and multi-size EXE icon at build time, without a shipped SVG renderer.
- Portable packaging contains a short guide, licenses, matching LGPL tray source, runtime and per-file checksums, not developer docs or audits.
- Shared per-user locks still prevent competing app copies while data remains portable.
- MIT licensing and the concise primary-source comparison remain in the public README.
- The user's installed App and Python package are 0.3.0, monitoring at Windows login, with all three clients, Detailed logging, unchanged Continue prompt and compact 8 MiB/three-backup retention.
- Previous deployments and original JSON/logs remain in recoverable ignored local staging; runtime data is excluded from artifacts.

## Verification

Native Windows 11 build 10.0.26300, PowerShell 7.6.6, Python 3.13.7, Codex CLI/daemon 0.160.0:

- Final native gate: 161 passed, no skips, 29.49 seconds; compileall and 0.3.0 version smoke passed.
- Real owned About dialog checks pass OK, X and Escape, with separate native tray/dialog threads and no held popup callback.
- Native HMENU lifetime/highlight checks remain green; no claim of a manual mouse-hover review.
- All eight interactive client combinations, comment-preserving TOML, safe pause/recovery, no-client no-connection behavior, local status, correlated scan output, prompt-preserving reset, asynchronous repair actions and fail-fast empty-prompt startup are covered.
- Frozen 0.3.0 probe passes spaces/percent paths, implicit defaults, local data, exclusive once, exact scan acknowledgement, same-PID settings/privacy reload, invalid settings/prompt pause and repair, and graceful stop.
- The isolated frozen probe uses no selected clients: zero Codex connections and zero user-chat dispatches.
- Final portable CRC and 521 file hashes, deployed hashes, source-wheel module/asset parity, dependency notices/source and repository Markdown targets are verified.
- The final update preserves all seven current data files byte-for-byte before activation. Original pre-TOML data and logs remain backed up.
- Actual login-shortcut launch reaches monitoring, three chats checked, zero detected/dispatched/pending. Installed CLI resolves App/data, reports 0.3.0 and confirms startup, all clients and Detailed telemetry.
- Local steady-scan samples show about 97% fewer bytes; gzip historical preservation is byte-exact after decompression. This is an observational sample, not a universal benchmark.
- Earlier real interactive CLI and Desktop-style separate-writer queue delivery remain evidence for unchanged interfaces.
- Natural quota-reset delivery, actual VS Code UI delivery, two simultaneous real quota failures, fresh login and external editor startup performance remain unobserved.
- Exact settings, bounds and limits are in Docs/VALIDATION.md and the retained implementation evidence.

## Artifacts

Shareable portable ZIP: `dist/codex-auto-continuer-0.3.0-windows-x86_64.zip`.

Optional wheel: `dist/codex_auto_continuer-0.3.0-py3-none-any.whl`.

Stable source transport: `codex-auto-continuer-codex-handoff.zip`.

The handoff includes source, tests, docs, helpers and audit state with hashes and Git provenance. It excludes App, runtime data, installed dependencies, build output and secrets. Packaging runs audit retention and transport validation.
