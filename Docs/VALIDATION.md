# Verification

Current verification: 3 October 2026. Application: 0.3.0. Imported base: verified ChatGPT v001, bootstrap commit `643ba04`. Earlier results remain in [the historical records](README.md#historical-records); dated observations have not been rewritten as current results.

## Environment and settings

| Item | Exact value |
| --- | --- |
| Operating system | Windows 11 build 10.0.26300, x86_64 |
| Shell | PowerShell 7.6.6 |
| Python | CPython 3.13.7 |
| Codex CLI and daemon | 0.160.0 |
| Tray and settings dependencies | pystray 0.19.5; Pillow 12.3.0 and TOMLKit 0.15.1 in the build environment |
| Source gate dependencies | Global Pillow 10.4.0 and TOMLKit 0.13.2; unrelated versions preserved |
| Portable builder | PyInstaller 6.22.3, hooks 2026.8; folder-mode GUI and console EXEs |
| SVG renderer | Build-only resvg-py 0.5.0; excluded from the runtime |
| Discovery | 24 hours from failed-turn completion; durable recorded obligations survive lookback |
| Clients | VS Code, CLI and Desktop selected; executor and sub-agent jobs always excluded |
| Poll interval | 30 seconds |
| RPC total deadline | 12 seconds |
| Codex subprocess deadline | 20 seconds with process-tree cleanup |
| Dispatch spacing | 2 seconds |
| Reconnect backoff | 5 seconds |
| Ambiguous-send recovery | 15 seconds; no blind retry |
| Daemon autostart | Enabled |
| Release telemetry | Private; compact summaries; trace disabled; 8 MiB per stream, three gzip backups |
| User deployment telemetry | Detailed; compact summaries; trace disabled; 8 MiB per stream, three gzip backups |
| Prompt | UTF-8 Markdown, default Continue; re-read before each send; maximum 64 KiB |
| Settings | Annotated TOML overrides; maximum 64 KiB; validated cycle-boundary reload |
| Tray controls | Serialized state-changing commands, 90s or 120s bounds; direct asynchronous file actions |
| Status | Local snapshot, one-second refresh; no Codex RPC for ordinary status |

## Native gate

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
```

Final result: 161 passed, no skips, in 29.49 seconds. Bytecode compilation and version smoke passed, reporting 0.3.0. The gate bounds pytest at 180 seconds, compileall at 120 seconds and version import at 30 seconds, with process-tree termination on timeout.

The retained safety suite covers structured quota authority, completion-time recency, exact targeting, durable state, same-second manual progress, final resume/quota checks, separate writers, multi-chat permission rechecks, exact stale queue deletion, ambiguous sends, protocol deadlines, native sockets and locks, shortcut ownership and quoting, and body/credential canaries.

New UX checks cover commented implicit defaults, comment-preserving tray edits, all eight client combinations, paused dispatch on invalid settings with preserved pending work, recovery after repair, no connection when all clients are disabled and state is empty, local-only status, request-correlated scan results, default restoration preserving a custom prompt and state, and file actions independent of busy monitor controls. Invalid prompts are reported before hidden startup.

Telemetry checks cover compact change-only events, per-cycle RPC timing aggregates, explicit dispatch events, exact gzip preservation and both privacy modes. Nested sub-agent provenance is reduced to its source kind; parent IDs, role text and nicknames cannot leak through that nested payload. Custom-source names obey the same privacy rule as other names.

## Native menu and dialogs

The Win32 popup-lifetime adapter remains in place. Real HMENU regressions preserve Windows' MFS_HILITE state during background and selected-item callbacks, prevent reentrant replacement, and refresh labels/checkmarks/enabled states on the next opening. Native tracking, foreground and cursor calls are intercepted; this is not a visual mouse-hover review.

Three tests exercise actual owned Windows About dialogs with the real tray UI loop. About runs on a separate native thread; the popup callback has returned before interaction. The tests close the actual OK button, post X closure and post Escape. Each completes without leaving a pending dialog. Button delivery uses a one-second SendMessageTimeout bound and the whole focused check is bounded at 30 seconds. Only the tests' own windows are operated, never the user's installed app.

The native single-OK dialog may expose its OK button as IDCANCEL rather than IDOK; the probe checks the actual button label instead of assuming its numeric ID. About and confirmation dialogs have dedicated Windows owners and do not occupy the monitor-control worker.

The observed old About path invoked an unowned modal dialog directly inside the right-click callback. That structural blocking path has been removed. The user's exact physical old-window failure was not replayed by operating their active desktop.

## Frozen release probe

```powershell
& './scripts/run-project-command.ps1' -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/History/2026-10-03-ux-release/probe_portable.py') -TimeoutSeconds 150
```

The final 0.3.0 ZIP passed from an owned path containing spaces and a percent sign. Command bounds are 20 seconds, graceful stop 65 seconds, state waits 15 seconds, outer bound 150 seconds. The probe uses an isolated control directory and `clients = []`, with a one-second poll interval. It makes zero Codex connections and zero user-chat dispatches.

Verified: 521 manifest-listed release files, ZIP CRC and SHA-256 checks, original dependency notices and matching LGPL tray source, no developer Docs/runtime data/renderer in the release, short README parity, implicit default settings without creating a file, local portable data, default Continue prompt, exclusive-once protection, scan acknowledgement and completed counts, privacy hot reload with the same PID, invalid-settings pause/repair with the same PID, invalid-prompt pause/repair with the same PID, and graceful stop.

[The integration sources](History/2026-10-03-ux-release/RESULTS.md) retain the probe and exact measured results. Earlier real interactive CLI and Desktop-style separate-owner queue delivery remain evidence for unchanged recovery interfaces. They were not re-run merely to increase test counts. The actual VS Code extension UI remains unverified.

## Package integrity

```powershell
pwsh -NoProfile -File scripts/build-portable.ps1
& './scripts/run-project-command.ps1' -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/History/2026-10-03-ux-release/probe_integrity.py') -TimeoutSeconds 40
```

The builder is bounded at 360 seconds, PyInstaller at 300 seconds. It renders the SVG before packaging, includes notices and matching tray source, and verifies every manifest hash and ZIP CRC. The integrity probe verifies deployed release-file hashes, source-wheel module/asset parity, MIT/runtime dependency metadata and all repository Markdown file targets.

Shareable artifact: `dist/codex-auto-continuer-0.3.0-windows-x86_64.zip`, 16,299,281 bytes. SHA-256: `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`.

Wheel: `dist/codex_auto_continuer-0.3.0-py3-none-any.whl`. Stable source handoff: `codex-auto-continuer-codex-handoff.zip`. Runtime data, App, installed dependencies, renderer binaries, toolchains and build output are excluded from source transport.

## Installed activation and log size

The deployment is `App/CodexAutoContinuer.exe`, with annotated settings under `App/data/settings.toml`. The original JSON is retained in a recoverable previous-App backup, not used as a second active format. The saved nine-byte Continue prompt has unchanged SHA-256 `adb2540b253f1647fc7311e6085e4ab2d8c3425579873ed4d51ec2b373c794f3`. Detailed logging remains selected.

The final deployment stopped the verified old supervisor gracefully and checked the exact tray executable/command line before stopping it. All seven current data files matched their backup hashes before activation. Previous App folders remain in ignored local staging for recovery. No pending obligations were present; state was not manufactured or deleted.

The managed Startup shortcut targets the GUI EXE with `--config "...App/data/settings.toml" tray`. Actual shortcut launch emitted tray.ready for 0.3.0 and reached monitoring with three chats checked and zero detected/dispatched/pending. All 521 deployed release files match the final manifest. The installed Python package also reports 0.3.0 and controls the registered App copy. Startup and Detailed telemetry are enabled. Unrelated global dependency versions remain intact.

A short observational comparison used the same host, all three clients, three recent chats, 30-second polling and Detailed privacy. Ten old completed intervals averaged 32,876.9 bytes and 26 events; four initial new intervals averaged 971.5 bytes and two events, with zero dispatches in both samples: about 97.0% fewer bytes. Startup was excluded. This is a local sample, not a universal benchmark or a completeness proof.

The old 15,688,423-byte telemetry stream became a 1,846,324-byte gzip backup. Decompression matched the original backup byte-for-byte. Existing logs were preserved, not scrubbed.

## Remaining limits

- Actual VS Code extension UI delivery and a natural account-reset automatic continuation have not been observed. Shared-protocol support is an inference where direct evidence is unavailable.
- Two simultaneous real quota failures were not available; multi-chat safety is covered by regression fixtures.
- Shortcut launch is verified, not a fresh Windows login.
- Native dialog/button checks are not a manual mouse or screen-reader review. Associated-editor target and asynchronous launch are tested, not external editor startup performance.
- Queue addition has no verified atomic turn precondition or idempotency contract. Immediate revalidation cannot eliminate every concurrent-progress race.
- Subsequent-turn telemetry reports observed metadata, not guaranteed attribution to a queued message.
- Other Windows/Codex installations must pass capability checks. EXEs are unsigned; SmartScreen reputation and other machines have not been tested.
