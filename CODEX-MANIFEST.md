# Codex manifest

ChatGPT base checkpoint: v001

Updated: 2026-10-04

## Imported base

All 46 imported checksum entries were verified. Standalone Git bootstrap `643ba04` preserves v001 and its original checksum manifest. ChatGPT's manifest is unchanged. The stale imported checksum file is not retained as a current-source checksum; each new transport owns its generated manifest.

## Local product changes since the base

- Native Windows socket transport, exact-thread separate-writer queue handling, quota-only authority, 24-hour discovery, durable obligations, stale cancellation and conservative ambiguous-send recovery.
- Portable 0.3.0 Windows tray and companion CLI, shared per-user locks, owned non-blocking native dialogs, preserved popup highlights, per-user login launch and independent interactive-client choices. Executor/sub-agent jobs remain excluded.
- Annotated TOML overrides with implicit defaults, comment-preserving edits and safe cycle-boundary reload. Invalid settings or prompts pause dispatch and preserve pending work. Saved Markdown defaults to Continue and is re-read before every send.
- Compact local telemetry with Private/Detailed modes, keyed private IDs, allowlisted tracing, RPC/cycle aggregates, explicit recovery events and compressed rotation. Conversation bodies, credentials, raw RPC payloads and nested excluded sub-agent provenance are not logged.
- Lossless SVG-derived green/yellow/red assets; clean one-folder builds with a short guide, licenses, corresponding tray source and checksums, without developer records or runtime data.
- The installed App and Python package remain 0.3.0. All three clients, Detailed logging and Windows login startup remain enabled locally. The existing Continue prompt and runtime data were not changed by publication work.

## Publication work

The user chose one public repository. Sanitized audits, history and ChatGPT/Codex manifests remain Git-tracked; no separate public checkout, historical rewrite or GitHub upload was performed.

- Git and source-export exclusions now protect root portable data, root runtime settings/prompt/state/logs, any root log backup count and environment-file variants. Synthetic regression canaries prove the source boundary; custom locations still need explicit exclusions.
- The Windows gate uses the local venv without a second global install, supports explicit interpreter selection and fails clearly on a wrong Python version.
- Native socket fixtures use short ignored checkout-local staging. This fixes the observed host-specific system-temp fixture failure; the actual daemon connection works and production socket code is unchanged.
- README and docs navigation prioritize usage, source setup/build, safety and current evidence. Contributor and security guides distinguish public development records from lean app releases. Prior 0.3.0 verification is dated in history, and rotated-audit links resolve.
- Windows CI uses commit-pinned official actions, read-only permissions, no persisted checkout credentials and bounded commands. It builds ZIP/wheel artifacts, never publishes a release automatically.

## Verification

Windows 11 build 10.0.26300 x86_64; PowerShell 7.6.6; CPython 3.13.7; Codex CLI/daemon 0.160.0.

- Final native gate: 163 passed, no skips/warnings, 49.34s; compileall includes integration sources and 0.3.0 version smoke passed. Explicit interpreter selection was previously exercised.
- Fresh self-contained 96-file source export: new venv installation, 163 tests in 54.69s, portable build, wheel build and frozen UX probe passed without a parent checkout or existing installation.
- Frozen probe: isolated controls, no clients, one-second polling; implicit defaults, Continue, scan feedback, exclusive once, same-PID reload and settings/prompt pause/repair, graceful stop; zero Codex connections and zero user-chat dispatches.
- Initial privacy inventory: all five existing commits, 171 distinct blobs, working tree, portable ZIP and wheel; no credential/profile/project-path matches, runtime files or private author emails. Pre-delivery scanning includes updated source and the source handoff.
- Deep frozen inspection: both executable CArchives/PYZ archives, nested stdlib ZIP and 440 bytecode modules/code filenames; no personal build paths found.
- Actual deployed 521 release hashes, wheel source/asset parity, licenses/source and repository Markdown file targets pass. Current portable bytes are unchanged; wheel README metadata is refreshed.
- Audit cleanup reports zero deletions. No production monitor was restarted or live user chat resumed during this audit.
- GitHub-hosted CI, natural quota-reset delivery, actual VS Code UI delivery, fresh login, manual visual/accessibility review and other Windows installations remain unobserved. EXEs are unsigned and queue concurrency/idempotency limits remain documented.
- Five failed system-temp socket fixtures remain outside the repo because the host rejected their exact scoped cleanup. Successful fresh staging/fixtures clean up normally and no failed fixture is in an artifact.

Exact settings, commands and limits are in Docs/VALIDATION.md and the dated publication audit.

## Native continuation tests

Added a standalone eight-scenario pytest suite and bounded `scripts/verify-continuation.ps1` gate. It uses unmodified installed Codex 0.160.0, two isolated native app-server owners, synthetic file-backed authentication and local model/account service responses. No user credentials, chats, allowance or deployed settings were used or changed. Runtime code and portable EXEs are unchanged.

The native chain covers persisted quota failure, durable detection, denied waiting despite an expired reset, exact saved-prompt queue submission and successful completion on the original writer. Additional scenarios cover account/user identity validation, unrelated/manual chats, invalid/repaired prompts, two-chat permission checks, lost acknowledgement, unaccepted writes, state reload without duplicates and compact Private telemetry. Final native integration: 8 passed, no skips/warnings, 60.77s. Exact results are in Docs/VALIDATION.md.

The regular Windows gate remains independent of Codex installation. Integration requires the native executable and fails rather than skipping if unavailable. Docs/CONTINUATION-TESTS.md records all boundaries and reproduction settings. Native service mocks are not claims of a natural quota reset, real extension/Desktop UI, production daemon discovery, tray process restart or atomic/idempotent queue guarantees.

Follow-up privacy inspection covered all 101 source files, existing history, unchanged portable ZIP and refreshed wheel. No privacy matches, private author emails, tracked runtime data or broken Markdown file targets were found. All native fixture directories cleaned up; the installed tray/supervisor PIDs were unchanged. Audit cleanup reported zero deletions.

## VS Code extension verification

Added the separate, explicit `scripts/verify-vscode.ps1` gate with installed editor/extension paths. It runs the original installed bundle and native executable in an isolated VS Code extension host. A disposable bootstrap installs read-only process-transport taps before activation; no installed source is patched. Initial thread/turn RPCs are test-driven, so visual composer/rendering behavior is not claimed.

VS Code 1.140.0, official openai.chatgpt 26.930.41038 and bundled Codex 0.160.0 passed all eight client-selection combinations, three denied quota scans, durable exact-thread state, one original-owner Continue/completed turn, three duplicate-prevention scans and Private telemetry assertions. Before-and-after hashes prove the installed manifest, bundle and native executable are unchanged. Extension gate: one passed in 15.80s; native eight-scenario rerun: 8 passed in 60.31s. Source filtering already matches the actual metadata, so runtime code and portable EXEs are unchanged.

The local rejecting proxy counts expected blocked workbench/extension external requests separately; unexpected native account/model routes and invalid synthetic authorization still fail. Test-only profiles, chats and processes cleaned up. User authentication, normal editor profile, deployed CAC data/prompt and installed tray/supervisor processes were untouched. Documentation now distinguishes verified extension ownership from unobserved visual UI and describes generic vscode-source app-server classification accurately.

Contributor array-argument commands now invoke the PowerShell runner directly; nesting `pwsh -File` flattened their arrays and misbound pip's timeout option. The corrected bounded wheel command passed, refreshing only README metadata.

Pre-commit privacy inspection covered seven existing commits, 204 unique blobs, all 105 source files, the unchanged portable ZIP and refreshed wheel. No credential/profile/project-path matches, tracked runtime data, private author emails or broken Markdown file targets were found. Audit cleanup reported zero deletions. All test homes cleaned up; installed CAC PIDs remained unchanged. Scoped commit and stable source transport retain the repeatable tests without shipping them in the portable app.

## Artifacts

Portable: `dist/codex-auto-continuer-0.3.0-windows-x86_64.zip`, SHA-256 `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`.

Optional wheel: `dist/codex_auto_continuer-0.3.0-py3-none-any.whl`, README metadata refreshed, SHA-256 `4e690e28bdb7ae36ac267c93ae40952a65645d9caceb3191605251b897bc3ef8`.

Stable source transport: `codex-auto-continuer-codex-handoff.zip`. It includes useful public development records and audit state with per-file hashes and Git provenance, excluding runtime data, App, dependencies, build output and secrets. Packaging runs retention and transport validation.
