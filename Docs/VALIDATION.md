# Verification

Current release: CAC 0.5.1, 4 October 2026. Local environment: Windows 11 build 10.0.26300 x86_64, PowerShell 7.6.6 and CPython 3.13.7. Hosted builds use Windows Server 2025 and CPython 3.13.15. Imported checkpoint: v001. [Dated 0.4.0 verification](History/2026-10-04-native-0.4.0-validation.md) preserves earlier results.

## Recovery and compatibility

| Check | Scope | Result |
| --- | --- | --- |
| `scripts/verify-windows.ps1` | Unit/workflow regressions, compileall and release import | 228 passed in 36.37 seconds; CAC 0.5.1 |
| `scripts/verify-continuation.ps1` | Official native Codex, two separate owners and managed lifecycle | 11 passed in 89.58 seconds |
| Hosted compatibility matrix | Baseline, stable and independently selected daemon packages | 11 passed per job; 104.77, 104.56 and 120.02 seconds; schema checks passed |
| Signed release workflow | Windows gate, official native baseline, build, signing and publication | Passed; release source `f3cf72f` |

The certified CLI and managed-daemon executable are official Windows Codex 0.160.0, SHA-256 `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`. The consumer-schema hash is `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`. Current stable also resolves to 0.160.0: the mixed-package matrix does not establish compatibility between genuinely different releases yet.

Hosted evidence: [compatibility matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37207915826), [Windows build](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37207915787) and [signed release](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37207020448). These links require access while the repository is private.

Managed tests exercise production discovery, handshake, generated schema, reconnect and restart identity. Removing certification proves Strict preserves pending-state bytes without submitting. Balanced then recovers the same untested stable tuple. Each verifies one saved Continue on the separate owner and no later duplicate. Unit regressions quarantine an ambiguous chat without blocking another safe chat, never retry uncertain intent, and retain observations when persisted terminal status lacks a completion timestamp.

Native probes use isolated homes, synthetic authentication and loopback account/model services. No real login, allowance or user chats are used. [Native test documentation](CONTINUATION-TESTS.md) owns the complete settings, deadlines, scenarios and reproduction commands. Hosted setup uses a disposable standard account and batch-logon right, without changing Codex's elevation guard. RPC deadlines match production; cold package bootstrap has its own bounded setup budget. Earlier hosted failures were fixture startup/elevation/job/logon restrictions and timing, not silently skipped assertions.

One real quota recovery was observed in a Desktop chat on an earlier CAC build. [Dated natural evidence](History/2026-10-04-natural-recovery.md) records detection, permission, one queue acknowledgement, Continue/start and later completion, including causal and observation limits.

## Signed update checks

Focused updater/native-process regressions passed 30 tests in 1.71 seconds. Fixtures cover signature tampering, wrong publisher/platform/state schema, duplicate JSON, traversal, links, device names, case collisions, redirect credential stripping, slow responses, partial copying, interrupted backup moves and automatic code rollback after startup failure. A real Windows child-process regression verifies that an exited process with retained handles is not mistaken for an unreadable live process. Actual Windows reader-lock tests verify bounded atomic-write recovery and persistent-lock failure without losing saved files.

The real frozen update probe passed twice against the private GitHub release:

```powershell
& ./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('scripts/verify-update.py','--baseline-archive','dist/codex-auto-continuer-0.4.0-windows-x86_64.zip','--private') -TimeoutSeconds 400
```

The probe starts retained 0.4.0 binaries in isolated controls, downloads and verifies the signed 0.5.1 GitHub package, completes replacement and startup health checks, then performs code-only rollback. Settings, saved prompt and uncertain state remain byte-identical through upgrade. State written after upgrade survives rollback; all 525 original code-file hashes match. A deliberately absent Codex executable prevents user connections or dispatches. Upgrade completion is read from the durable job journal, not the latest-check snapshot, which subsequent release checks may replace.

## Package and privacy

The GitHub-built portable package passed the frozen UX probe: 581 manifest files, both EXEs, implicit defaults, spaces/percent paths, same-PID settings reload, invalid-settings/prompt pause and repair, correlated scan feedback, exclusive one-cycle execution and graceful stop. Zero Codex connections or user chats were used. Manifest checks verify exact bytes; guide-content parity permits normal Git line-ending conversion. The package contains the short guide, code and legal notices, not developer records or runtime data.

| Published asset | Bytes | SHA-256 |
| --- | --- | --- |
| `codex-auto-continuer-0.5.1-windows-x86_64.zip` | 20,189,673 | `a4b0718fb062b35fd0284be2cfccadf041e5c544f02c2b3558b40ccdd365df62` |
| `codex_auto_continuer-0.5.1-py3-none-any.whl` | 101,248 | `c063648868050cd1cfb04a5d3b3b383d8c6991143a8e5455d1b00b84784d1ea4` |

Local `dist` copies are the exact published assets, not separately rebuilt substitutes. The [private stable release](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.5.1) also contains detached signed update metadata. The failed 0.5.0 validation build is an unpublished draft, not a stable update candidate. No public availability is asserted.

Privacy inspection covers every Git commit/blob, non-ignored source, Markdown targets, source transport, wheel, both executable archives, nested standard-library archives and 481 bytecode modules/code filenames. It found no credential/profile/project-path matches, private author emails, tracked runtime files or broken file links. Synthetic export canaries cover user settings, state, telemetry, notification/update status and code-recovery folders. The signing key is encrypted locally, ignored and excluded from transports; only its public key is tracked. GitHub Actions holds the signing secret, with publication permissions isolated to the release workflow.

## Installed app

The existing App was upgraded from 0.4.0 through the verified GitHub package and external worker. The durable journal reports completed; all 581 installed code hashes match. Settings, Continue prompt and state hashes matched before and after replacement. Private-release authentication was then explicitly enabled and new annotated default comments added, preserving all three selected clients and Detailed logging.

The tray and supervisor run CAC 0.5.1 at the existing App path. Live status reports monitoring, certified Codex 0.160.0, Balanced policy, permitted writes and zero pending obligations. Signed automatic CAC updates are enabled; an authenticated release check reports current. The original login shortcut still targets this App and settings path. No user Codex executable, home or authentication was replaced.

## Environment and limits

Runtime dependencies: pystray 0.19.5, Pillow 12.3.0, TOMLKit 0.15.1, six 1.17.0, Cryptography 48.0.1, CFFI 2.1.1 and pycparser 3.0. Build tools: PyInstaller 6.22.3 and resvg-py 0.5.0.

The installed VS Code native-owner/filtering evidence is retained in the dated 0.4.0 record. A fresh 0.5.1 extension run was unavailable because that extension is no longer registered in the inspected local profile. Client-filtering code is unchanged; visual composer/rendering is not claimed. Fresh Windows login, another user's hardware and Windows reputation acceptance remain outside automated verification.

Schemas do not establish future queue semantics or atomic/idempotent submission. The running writer's executable bytes are not universally exposed upstream. Update replacement is recoverable, not power-loss-atomic. EXEs are not Authenticode-signed; Ed25519 update verification does not remove Windows reputation prompts. [Compatibility](COMPATIBILITY.md), [architecture](ARCHITECTURE.md) and [updates](UPDATES.md) own those safety boundaries.
