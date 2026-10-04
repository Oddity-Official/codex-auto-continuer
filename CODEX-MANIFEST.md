# Codex manifest

ChatGPT base checkpoint: v001

Updated: 2026-10-04

## Imported base

All 46 imported checksum entries were verified. Standalone Git bootstrap `643ba04` preserves v001 and its original checksum manifest. ChatGPT's manifest is unchanged. The stale imported checksum file is not retained as a current-source checksum; each new transport owns its generated manifest.

## CAC 0.5.2 local work

- Completed the user-authorized isolated queue-control investigation: 7 native probes passed in 44.39 seconds. Full history preserves consumed queue client identity; owner interruption pauses the queue; owner selected-start prioritizes literal Continue. A synthetic outbox also held inputs through renewed denied permission and released them one at a time after fresh permission checks. Cross-owner interruption/start and in-place removal were rejected. A before-turn recovery fork works but changes thread identity. No production queue mode, durable private journal, prompt wrapper, installed binary or runtime change was made. Dated evidence is in `Docs/Audits/2026-10-04-02/`.

- Investigated the red status against private metadata and session lifecycle. An internal read-only quota RPC error stopped monitoring before reset; the pending obligation remained durable. Restart restored monitoring. Queued follow-ups failed with structured quota errors but did not erase the obligation.
- Retry only internal account-usage read errors, preserving state and withholding current permission. Retain pending count, last scan, compatibility and safe method/code in status; other contract/request/mutation errors still fail diagnostically. Check For Updates now sits immediately above About.
- Added a real native queued-failure/HTTP-503/recovery scenario and focused regressions. Fixture reconnects remain on the synthetic socket. No conversation-body storage, queue interception or text-equality delivery assertion was introduced.
- Focused development commands, documentation-only CI, consumed-input workflow filters and exact-tuple deduplication reduce repeated release work. Completed deliveries still receive source handoffs. Shared policy snapshots preserve portable project ownership.
- Published private 0.5.2 from `08d74f3` after hosted Windows, native and release checks. Verified the downloaded frozen package, then upgraded the actual App through the signed updater. The durable install job completed, all 581 installed hashes match, and settings/prompt/state hashes are unchanged. App monitoring and the existing login shortcut are intact. Exact artifacts and limits are recorded in `Docs/VALIDATION.md`.
- The shared setup/template bundle now lives in the local `_ProjectSupport/_workflow` repository with policy and lessons. New installations embed the current policy; deployed projects remain independent. The Writing location retains only a pointer.
- Source/history and exact published ZIP/wheel/handoff privacy inspection passed without detected runtime, credential or compiled personal-path leakage. Documentation-only hosted checks passed without a new binary/native run. The repository remains private; no user-message storage or replay was added.
- The approved dark tray/status presentation choices are not claimed implemented by this recovery patch. Native computer control remains unavailable in this session's tool surface, unrelated to CAC's prohibition on automating Codex for dispatch.

## CAC 0.5.1 implementation

- Balanced defaults permit schema-verified stable Codex builds; Strict retains exact-build certification. Status explains evidence and unknown builds get deduplicated non-modal notices.
- Unresolved ambiguous submissions isolate only their chat without retrying. Delivery observations require terminal completion evidence, preserving separate-writer incomplete history across restart.
- Signed stable CAC updates pin a publisher key, verify archive/file checksums, keep downloads off monitoring controls, finish cycles before replacement and preserve current runtime state through code-only rollback. The publisher key is encrypted locally and excluded from source; CI receives it through a GitHub Actions secret.
- The authorized publisher repository is private `Oddity-Official/codex-auto-continuer`, with source pushed and signed 0.5.1 published. Windows verification, the complete hosted native matrix, the GitHub-built frozen UX package and real 0.4.0 upgrade/code-only rollback passed. Current commands, results, hashes and limits are owned by Docs/VALIDATION.md.
- Real Windows regressions cover exited processes with retained handles and transient atomic-file sharing locks. CI uses a disposable standard account with a scoped batch-logon right, production RPC deadlines and a bounded cold-package budget. A running scheduled action establishes launcher liveness even before its first log; security guards and assertions are not bypassed.
- Installed App 0.5.1 reports monitoring/certified under Balanced policy. All 581 installed code hashes match the signed package. Settings, Continue and state hashes survived replacement; private GitHub authentication and annotated new settings were then explicitly enabled without changing client/logging preferences. The existing login shortcut is intact. Code recovery remains local; ChatGPT's manifest is unchanged.

## Local product changes since the base

- Native Windows socket transport, exact-thread separate-writer queue handling, quota-only authority, 24-hour discovery, durable obligations, stale cancellation and conservative ambiguous-send recovery.
- Portable 0.5.1 Windows tray and companion CLI, shared per-user locks, owned non-blocking native dialogs, preserved popup highlights, per-user login launch and independent interactive-client choices. Executor/sub-agent jobs remain excluded.
- Annotated TOML overrides with implicit defaults, comment-preserving edits and safe cycle-boundary reload. Invalid settings or prompts pause dispatch and preserve pending work. Saved Markdown defaults to Continue and is re-read before every send.
- Compact local telemetry with Private/Detailed modes, keyed private IDs, allowlisted tracing, RPC/cycle aggregates, explicit recovery events and compressed rotation. Conversation bodies, credentials, raw RPC payloads and nested excluded sub-agent provenance are not logged.
- Lossless SVG-derived green/yellow/red assets; clean one-folder builds with a short guide, licenses, corresponding tray source and checksums, without developer records or runtime data.
- All three clients, Detailed logging, Balanced compatibility, automatic signed updates and Windows login startup are enabled locally. The Continue prompt and runtime data remain intact. Private-release access uses the existing GitHub CLI login in memory; credentials are not logged, saved in CAC or bundled.

## Publication work

The user chose one repository for public sharing, then authorized creating and testing it privately under Oddity-Official. Sanitized audits, history and ChatGPT/Codex manifests remain Git-tracked and uploaded; no separate public checkout or history rewrite was performed. App, runtime data, private signing material and recovery folders remain excluded. The repository has not been made public.

- Git and source-export exclusions now protect root portable data, root runtime settings/prompt/state/logs, any root log backup count and environment-file variants. Synthetic regression canaries prove the source boundary; custom locations still need explicit exclusions.
- The Windows gate uses the local venv without a second global install, supports explicit interpreter selection and fails clearly on a wrong Python version.
- Native socket fixtures use short ignored checkout-local staging. This fixes the observed host-specific system-temp fixture failure; the actual daemon connection works and production socket code is unchanged.
- README and docs navigation prioritize usage, source setup/build, safety and current evidence. Contributor and security guides distinguish public development records from lean app releases. Prior 0.3.0 verification is dated in history, and rotated-audit links resolve.
- Ordinary Windows and compatibility CI use commit-pinned official actions, read-only permissions, no persisted checkout credentials and bounded commands. A separate trusted release workflow has signing/publication permission and publishes verified stable ZIP/wheel/signature assets. The 0.5.0 validation build is an unpublished draft.

## Publication verification (0.3.0)

Windows 11 build 10.0.26300 x86_64; PowerShell 7.6.6; CPython 3.13.7; Codex CLI/daemon 0.160.0.

- Final native gate: 163 passed, no skips/warnings, 39.16s; compileall includes integration sources and 0.3.0 version smoke passed. Explicit interpreter selection was previously exercised.
- Fresh self-contained 96-file source export: new venv installation, 163 tests in 54.69s, portable build, wheel build and frozen UX probe passed without a parent checkout or existing installation.
- Frozen probe: isolated controls, no clients, one-second polling; implicit defaults, Continue, scan feedback, exclusive once, same-PID reload and settings/prompt pause/repair, graceful stop; zero Codex connections and zero user-chat dispatches.
- Initial privacy inventory: all five existing commits, 171 distinct blobs, working tree, portable ZIP and wheel; no credential/profile/project-path matches, runtime files or private author emails. Pre-delivery scanning includes updated source and the source handoff.
- Deep frozen inspection: both executable CArchives/PYZ archives, nested stdlib ZIP and 440 bytecode modules/code filenames; no personal build paths found.
- Actual deployed 521 release hashes, wheel source/asset parity, licenses/source and repository Markdown file targets pass. Current portable bytes are unchanged; wheel README metadata is refreshed.
- Audit cleanup reports zero deletions. No production monitor was restarted or live user chat resumed during this audit.
- GitHub-hosted CI, natural quota-reset delivery, actual VS Code UI delivery, fresh login, manual visual/accessibility review and other Windows installations remain unobserved. EXEs are unsigned and queue concurrency/idempotency limits remain documented.
- Five failed system-temp socket fixtures remain outside the repo because the host rejected their exact scoped cleanup. Successful fresh staging/fixtures clean up normally and no failed fixture is in an artifact.

Exact settings, commands and limits are in Docs/VALIDATION.md and the dated publication audit.

## Native continuation tests (0.3.0)

Added a standalone eight-scenario pytest suite and bounded `scripts/verify-continuation.ps1` gate. It uses unmodified installed Codex 0.160.0, two isolated native app-server owners, synthetic file-backed authentication and local model/account service responses. No user credentials, chats, allowance or deployed settings were used or changed. Runtime code and portable EXEs are unchanged.

The native chain covers persisted quota failure, durable detection, denied waiting despite an expired reset, exact saved-prompt queue submission and successful completion on the original writer. Additional scenarios cover account/user identity validation, unrelated/manual chats, invalid/repaired prompts, two-chat permission checks, lost acknowledgement, unaccepted writes, state reload without duplicates and compact Private telemetry. Final native integration: 8 passed, no skips/warnings, 60.77s. Exact results are in Docs/VALIDATION.md.

The regular Windows gate remains independent of Codex installation. Integration requires the native executable and fails rather than skipping if unavailable. Docs/CONTINUATION-TESTS.md records all boundaries and reproduction settings. Native service mocks are not claims of a natural quota reset, real extension/Desktop UI, production daemon discovery, tray process restart or atomic/idempotent queue guarantees.

Follow-up privacy inspection covered all 101 source files, existing history, unchanged portable ZIP and refreshed wheel. No privacy matches, private author emails, tracked runtime data or broken Markdown file targets were found. All native fixture directories cleaned up; the installed tray/supervisor PIDs were unchanged. Audit cleanup reported zero deletions.

## VS Code extension verification (0.3.0)

Added the separate, explicit `scripts/verify-vscode.ps1` gate with installed editor/extension paths. It runs the original installed bundle and native executable in an isolated VS Code extension host. A disposable bootstrap installs read-only process-transport taps before activation; no installed source is patched. Initial thread/turn RPCs are test-driven, so visual composer/rendering behavior is not claimed.

VS Code 1.140.0, official openai.chatgpt 26.930.41038 and bundled Codex 0.160.0 passed all eight client-selection combinations, three denied quota scans, durable exact-thread state, one original-owner Continue/completed turn, three duplicate-prevention scans and Private telemetry assertions. Before-and-after hashes prove the installed manifest, bundle and native executable are unchanged. Extension gate: one passed in 15.80s; native eight-scenario rerun: 8 passed in 60.31s. Source filtering already matches the actual metadata, so runtime code and portable EXEs are unchanged.

The local rejecting proxy counts expected blocked workbench/extension external requests separately; unexpected native account/model routes and invalid synthetic authorization still fail. Test-only profiles, chats and processes cleaned up. User authentication, normal editor profile, deployed CAC data/prompt and installed tray/supervisor processes were untouched. Documentation now distinguishes verified extension ownership from unobserved visual UI and describes generic vscode-source app-server classification accurately.

Contributor array-argument commands now invoke the PowerShell runner directly; nesting `pwsh -File` flattened their arrays and misbound pip's timeout option. The corrected bounded wheel command passed, refreshing only README metadata.

Pre-commit privacy inspection covered seven existing commits, 204 unique blobs, all 105 source files, the unchanged portable ZIP and refreshed wheel. No credential/profile/project-path matches, tracked runtime data, private author emails or broken Markdown file targets were found. Audit cleanup reported zero deletions. All test homes cleaned up; installed CAC PIDs remained unchanged. Scoped commit and stable source transport retain the repeatable tests without shipping them in the portable app.

## Icon contrast (0.3.0)

Changed the SVG stack to off-white (#f1f5f9), with a subtle darker outline (#64748b) and white upper facet. Green/yellow/red arrow colors and recovery behavior are unchanged. Regenerated all three PNG states and rebuilt the portable EXEs/ZIP and wheel. Existing icon parity/state-color regression passed; generated 16px and 32px tray samples retain bright opaque stack pixels.

Activated the rebuilt App after gracefully stopping monitoring and verifying the exact tray process. All seven runtime files matched their preserved hashes before activation; settings, prompt, pending state, logs and Windows startup path were preserved. Previous App remains in an ignored local recovery folder. The deployed 521 release-file hashes and source/wheel assets match.

Windows gate: 163 passed, no skips/warnings, 39.16s; compileall and version smoke passed. Audit cleanup deleted nothing. Pre-commit privacy scan covered eight existing commits, 217 blobs and 105 source files, plus deep inspection of both rebuilt EXEs, 440 bytecode modules and the wheel. No credential/personal-path matches, tracked runtime data, private author emails or broken Markdown file targets were found. The refreshed tray and supervisor are running with phase monitoring.

## Compatibility hardening (0.4.0)

Implemented CAC 0.4.0 from clean `6016c21`. A packaged exact-version/build certificate now gates ownership resume and queue writes. Fresh connections and pre-write checks verify CLI, daemon lifecycle, running user-agent version and managed binary identities. The managed binary generates a consumer-specific experimental schema. Prerelease/build suffixes remain intact; unrelated endpoints and unconsumed fields do not change the contract. Matching schemas alone do not grant dispatch.

Untested tuples preserve pending/uncertain/submitted obligations and continue safe read-only discovery. Read-contract or unverifiable-identity failures pause scanning too. The running monitor retries; red tray Status and CLI snapshots explain the block. Telemetry retains versions, checksums, transitions and sanitized verification failures, never raw schemas/RPC bodies or credentials. A daemon restart during a pre-write check is a retryable block, not an uncertain send.

Added checksum-verified official-package downloads, schema reports and daily/manual/PR/default-branch Windows compatibility CI. The matrix covers baseline/baseline, current stable/current stable and baseline/current-stable daemon. Short native-test worktrees avoid Windows socket limits. Reports expire after 14 days; CI never edits certificates or publishes releases. This repository has no remote, so hosted execution/scheduling remain unobserved.

Certification evidence: official Windows 0.160.0 CLI/daemon binary SHA-256 `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`; contract SHA-256 `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`. Final Windows gate: 194 passed in 33.81s; compileall/version passed. Native ten-case gate against the downloaded complete official package: 10 passed in 74.84s; separate-package schema/managed follow-up: 2 passed in 14.30s. Installed VS Code owner/filtering gate: one passed in 14.96s, with all eight client combinations and unchanged original-file hashes. Native connections/restarts assert the requested CLI/daemon versions and executable checksums, preventing a bootstrap substitution from creating a false CI pass.

Inspected the separate standalone app-server package rather than assuming its role. Its eight controlled queue cases passed, but the 0.160.0 managed lifecycle requires the full package's bin/codex.exe and rejected the standalone layout. The standalone executable has no schema generator. No certificate was issued; the gate rejects that identity rather than borrowing a same-version CLI schema. CI uses complete CLI packages for managed-daemon candidates.

Final portable/frozen UX checks passed, including 525 file hashes, controls, same-PID settings/prompt reload, repair, scan feedback and graceful stop, with no Codex connections or user-chat dispatches. One earlier invalid-prompt phase wait timed out and was not reproduced; timeout diagnostics now include sanitized phase/event context. No speculative runtime fix is claimed. Source/wheel/contract parity and deep privacy inspection of two EXEs, 441 bytecode modules and the wheel passed. The pre-commit inventory found no private values, tracked runtime data, private author emails or broken links in nine existing commits, 224 blobs and 117 source files.

Activated the new App after graceful monitor stop and exact tray identity checks. Eight runtime files matched preserved hashes before launch. All clients, Detailed logging, Continue and Windows login path remain intact; the previous App is retained as an ignored recovery copy. Frozen live status reports monitoring/certified, zero pending and zero dispatches in the sampled cycle. Audit cleanup deleted nothing. No user chat was deliberately resumed by a probe.

Native fixture homes/processes cleaned up. The host rejected recursive cleanup of downloaded probe packages; they remain ignored in .data and excluded from every public artifact.

Limits remain explicit: current stable is also 0.160.0, so real different-release mixed behavior awaits another stable build. Running versions/disk hashes cannot attest loaded bytes after an out-of-band same-version replacement, or discover every separate writer's binary. No queue atomicity/idempotency, natural account reset, visual extension rendering, fresh login or hosted-CI pass is claimed. Docs/COMPATIBILITY.md owns policy and Docs/VALIDATION.md owns current evidence. Previous 0.3.0 verification is retained in dated history.

## Artifacts

Portable: `dist/codex-auto-continuer-0.5.1-windows-x86_64.zip`, the exact published GitHub asset, SHA-256 `a4b0718fb062b35fd0284be2cfccadf041e5c544f02c2b3558b40ccdd365df62`.

Optional wheel: `dist/codex_auto_continuer-0.5.1-py3-none-any.whl`, the exact published GitHub asset, SHA-256 `c063648868050cd1cfb04a5d3b3b383d8c6991143a8e5455d1b00b84784d1ea4`.

Stable source transport: `codex-auto-continuer-codex-handoff.zip`. It includes useful public development records and audit state with per-file hashes and Git provenance, excluding runtime data, App, dependencies, build output and secrets. Packaging runs retention and transport validation.
