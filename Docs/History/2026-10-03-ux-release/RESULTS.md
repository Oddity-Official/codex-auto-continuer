# UX release implementation evidence

Recorded on 3 October 2026 for CAC 0.3.0, Windows 11 build 10.0.26300, PowerShell 7.6.6, CPython 3.13.7 and native Codex 0.160.0. This is implementation verification, not a new full audit. Current product claims and limitations belong to [Verification](../../VALIDATION.md).

## Checks and bounds

| Check | Exact scope and settings | Result |
| --- | --- | --- |
| Final native gate | `scripts/verify-windows.ps1`; global Python 3.13, Pillow 10.4.0, TOMLKit 0.13.2; pytest 180s, compileall 120s, version 30s | 161 passed, no skips, 29.49s; compile/version passed |
| Focused controls/privacy | `tests/test_tray_and_telemetry.py` and `tests/test_desktop_controls.py`; isolated build Python, Pillow 12.3.0, TOMLKit 0.15.1; outer 30s | 20 passed, 3.82s |
| Actual owned dialogs | Three parameterized OK/X/Escape tests inside a real tray UI loop; inspect only owned native thread windows; five-second state wait, one-second button-send timeout | All three close; dialog thread differs from tray thread; popup tracking has returned |
| Frozen portable | [probe_portable.py](probe_portable.py); temporary path with spaces and percent; isolated LOCALAPPDATA; clients=[]; poll=1s; command=20s, stop=65s, state wait=15s, outer=150s | Same-PID hot reload, invalid settings/prompt pause and repair, exact scan acknowledgement, exclusive once and graceful stop pass; zero Codex connections or chat dispatches |
| Build | `scripts/build-portable.ps1`; isolated builder, outer 360s, PyInstaller 300s; SVG rendering before freezing | 521 manifest-listed files, 16,299,281-byte ZIP; CRC and hashes pass; no Docs/runtime data/renderer |
| Source/deployment parity | [probe_integrity.py](probe_integrity.py), outer 40s; per-file SHA-256, wheel source/assets/metadata, repository link targets | Deployed manifest hashes, wheel parity, notices, MIT and links pass |

Portable SHA-256: `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`.

The frozen probe verifies a commented settings template and Continue prompt, private/detailed local telemetry, absent settings using defaults without creating a file, readable local status and protected snapshots when another command cannot acquire the lock. It operates its own extracted copy and uses no selected clients throughout monitoring.

Dialog tests deliver the actual native OK-button message with a bounded API call; they do not simulate a physical mouse click. Windows exposed the single OK button as IDCANCEL, so the probe discovers its button handle and verifies its label rather than assuming IDOK. Foreground/cursor/menu tracking are intercepted to avoid operating the user's desktop.

## Observational telemetry sample

[probe_telemetry.py](probe_telemetry.py) reads complete monitoring intervals and prints only aggregate counts and bytes, never chat metadata. Outer bound: 20 seconds. Its two positional arguments are the preserved old telemetry stream and current telemetry stream.

Shared sample settings: same host, native account/home, CLI+VS Code+Desktop selection, three recent interactive chats, 30-second poll interval, Detailed privacy, trace disabled, zero dispatches. Startup is excluded from completed-interval samples.

| Sample | Completed intervals | Mean bytes | Mean events | Chats checked |
| --- | --- | --- | --- | --- |
| 0.2.1 | 10 | 32,876.9 | 26.0 | 3 |
| Initial 0.3.0 monitoring | 4 | 971.5 | 2.0 | 3 |

Observed reduction: 97.0% fewer bytes per interval. This short local sample is not a universal performance benchmark, and event reduction alone does not prove diagnostic completeness. Regression checks separately preserve changed metadata, cycle/RPC aggregates, dispatch and error events.

The old stream was 15,688,423 bytes. Its compressed backup was 1,846,324 bytes. Gzip decompression matched the preserved original exactly. Neither privacy selection nor deployment scrubbed the original log.

## Installed boundaries

The original pre-TOML App remains under `.data/ux-release-4f539a6b5a5744119a7147e3b2e1900b/previous-App`. The immediately preceding deployment remains under `.data/ux-final-1c3097cf9b954a0199e06bd590c52ab3/previous-App`. These are ignored recovery copies, not shareable artifacts.

The final update stopped the supervisor gracefully, rechecked the tray PID against its exact executable and tray command, then moved only checked project-contained paths. All seven current data files matched backup hashes before activation. The original six pre-TOML files remain intact in the first backup; only settings were explicitly converted into the single active TOML format.

The saved Continue prompt retained SHA-256 `adb2540b253f1647fc7311e6085e4ab2d8c3425579873ed4d51ec2b373c794f3`. Detailed privacy remains enabled; retention is 8 MiB and three compressed backups. No pending state existed, and none was deleted or fabricated.

Actual managed-login-shortcut launch emitted tray.ready for 0.3.0 and reached monitoring with three chats checked, zero detected/dispatched/pending. Installed Python package 0.3.0 resolves App/data and confirms startup enabled and all clients selected. Final activation's supervisor PID was 4188; a PID is evidence for that activation only, not a future identity assertion.

No fresh login, external editor startup measurement, actual VS Code extension UI delivery or natural quota-reset dispatch was performed. Unchanged recovery interfaces retain earlier native evidence; see current verification for the full limits.
