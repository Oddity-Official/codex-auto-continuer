# Portable tray release audit

Audit date: 3 October 2026
Source base: native 0.1.0 commit `1ef490f3128427a4b21489b5bb74da0e42942fb0`, after verified ChatGPT checkpoint v001.
Scope: Windows tray controls, portable packaging, client coverage, prompt editing, local telemetry and release operations.

## Outcome

The native gate passed 132 tests with no skips. A real native tray menu exercised the supervisor controls. A separately owned interactive CLI chat completed an exact queued second turn. Extracted EXEs passed native control, privacy and restart probes.

The release uses structured quota authority and exact-thread recovery. It does not answer approvals, switch models, bypass usage limits or use desktop input automation.

## Environment and settings

Windows 11 build 10.0.26300 x86_64, PowerShell 7.6.6, Python 3.13.7, Codex CLI/daemon 0.160.0. Build environment: .venv, pystray 0.19.5, Pillow 12.3.0, PyInstaller 6.22.3, hooks 2026.8. pywinpty 3.0.2 is audit-only.

Recovery defaults: 24-hour failed-turn completion lookback, allInteractive scope, 30s polls, 12s total RPC deadline, 20s Codex child bound, 2s dispatch spacing, 5s reconnect, 15s ambiguity reconciliation and no blind retry. Release logging: private, 16 MiB and 8 backups per stream. User logging: detailed, 64 MiB and 16 backups per stream. Prompt: UTF-8 Markdown, maximum 64 KiB, re-read at send.

## Confirmed release gaps and repairs

| Gap or failure | Cause | Resolution and evidence |
| --- | --- | --- |
| No tray or portable launcher | CLI-only product surface and external Python dependency | Native pystray menu plus separate GUI/console EXEs, shared engine and bundled Python |
| Prompt edits required JSON changes and restart | Inline prompt loaded with settings | Canonical Markdown file read immediately before each send; exact associated-editor target tested |
| Default client scope omitted interactive CLI and extension | Desktop-specific filter | allInteractive default; exec/subAgent excluded; source/originator guard retained for Desktop-only |
| Multiple portable folders could duplicate monitoring | Instance control tied to local data would not coordinate copies | Shared per-user supervisor and tray OS locks; local data remains portable |
| Diagnostics could not explain a queued continuation's later outcome | Obligations were removed after progress without durable follow-up | Submitted observations survive restart and report subsequent turn metadata without claiming causal attribution |
| Tray privacy could remain stale after settings changed | Tray and supervisor own separate logging handlers | Tray stream reconfiguration plus supervisor restart; privacy regression and frozen toggle probe |
| Initial notice collection omitted pystray COPYING files | Filename selection matched LICENSE and only copying.txt | COPYING-prefix selection and corresponding source inclusion; final release notice inspection required |
| First CLI probe did not start a turn | PTY inherited TERM=dumb and showed a terminal warning | Explicit xterm-256color environment; no warning/approval auto-answer |
| Successful CLI probe exited with cleanup error | Windows process still held its working directory when TemporaryDirectory exited | Stop owned process tree and close PTY before deleting the owned directory; successful bounded rerun |

No unsupported queue idempotency or atomic compare-and-swap contract was invented. Unrelated queued messages remain protected.

## Native gate and regressions

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
```

Final gate: 132 passed, no skips, 29.25s. Compileall passed for src, tests and scripts; version smoke returned 0.2.0. Bounds: pytest 180s, compilation 120s, import 30s. Earlier release-round gates passed 131 tests in 28.78s and 26.44s. The final extra case verifies native Startup creation with built-in Windows PowerShell, not only PowerShell 7.

Meaningful added regressions cover prompt reload/empty-file refusal, durable delivery observations, active-runtime precedence, private correlated IDs, credential/body canaries including unknown error payloads, allowlisted numeric HTTP status, frozen launch/config paths, exact .md association, tray/CLI parity, privacy reconfiguration, registered CLI ownership, and native executable discovery. Existing transport, filesystem, socket and dispatch safety checks remain in the gate.

## Probe commands and results

Run from the checkout. Each command uses the bounded runner, which stops descendants on timeout.

```powershell
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments 'Docs/Audits/2026-10-03-02/probe_tray_native.py' -TimeoutSeconds 120
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments 'Docs/Audits/2026-10-03-02/probe_cli_queue.py' -TimeoutSeconds 100
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments 'Docs/Audits/2026-10-03-02/probe_portable.py' -TimeoutSeconds 160
```

Stop monitoring before the tray or portable probes. The CLI probe makes 2 small real model turns; it uses only an owned thread, then archives it. These are audit tools, not background production refreshes.

| Probe | Exact settings and bounds | Essential observed result |
| --- | --- | --- |
| Tray | Real pystray Win32 icon and HMENU; owned temporary config; existing daemon; start 15s, cycle 20s, scan 10s, stop 65s, one cycle 35s; outer 120s | nativeMenuItems=21, scanWokeSupervisor=true, gracefulStop=true, oneCycleDialog=true |
| Interactive CLI | One private temporary cwd; gpt-6-luna/low, read-only sandbox, approvals never, fixed token replies, no tools; --no-alt-screen and --no-daemon; TERM=xterm-256color; RPC 5s; first/second completion waits 35s; outer 100s | source=cli, originator=Codex Desktop, initialTurn=completed, verifiedSeparateWriter=true, queuedIdReturned=true, queuedTurn=completed |
| Portable EXEs | Clean ZIP extraction to an owned spaces/percent path; version/init/status/start/scan/competing once/privacy restart/stop; ordinary commands 45s, logging 90s, stop 65s, state waits 20s; outer 160s | localData=true, startScanStop=true, exclusiveOnce=true, settingsRestart=true, privateAndDetailedTelemetry=true |

Tray dialogs are intercepted in the owned probe and public menu callbacks invoked programmatically. A real native menu is created, but this is not manual mouse inspection. The Markdown association test checks the exact os.startfile target, not user-editor editing.

## Packaging and deployment contract

`scripts/build-portable.ps1` builds in .venv, with an outer 360s bound and PyInstaller 300s bound. It stages into a new owned directory, preserves the preceding release on failure, includes original dependency notices and matching pystray source, hashes every file and verifies ZIP CRC/hash results. It rejects runtime data.

The executable folder uses adjacent data. Shared control locks and the owner record remain per-user. A pip CLI attaches to the registered app copy instead of starting a second monitor with another config. A moved registered copy fails clearly until launched from its new location.

MIT licensing applies to our code. Dependency licenses and the replaceable LGPL tray library remain separate. No code-signing certificate is provided.

Both initial and final-code portable probes passed. The final-code probe includes the corrected COPYING notice collection and allowlisted error metadata. The deployed GUI was launched through its actual managed login shortcut; tray.ready and a monitoring snapshot were observed. First cycle: scanned=3, detected=0, dispatched=0, pending=0. The installed 0.2.0 Python CLI attached to this app copy. Detailed user logging is enabled; old empty state, logs and inline config are preserved. Final artifact identity is reported at delivery. User metadata remains only in ignored runtime files, never in this report or a transport.

## Limits and provenance

The public survey fetched 12 project/service documentation sources. README owns the concise comparison; Docs/RESEARCH.md records scope and authoritative links. This is not an exhaustive inventory, security audit or benchmark.

Actual VS Code extension UI delivery was unavailable; no extension installation was found in standard account directories. Its scope is fixture-tested and shared-protocol delivery inferred.

Natural account-reset automatic delivery, 2 simultaneous real quota failures and a fresh Windows login were not observed. Earlier native evidence separately establishes Desktop-style ownership, queue CRUD, detached completion, quota-failure persistence and real waiting/stale cancellation. It remains in the archived 0.1.0 audit.

A subsequent turn may have been caused by user progress. Queue acceptance is not atomic against a turn revision. These limits remain explicit rather than hidden behind retries or UI fallbacks.
