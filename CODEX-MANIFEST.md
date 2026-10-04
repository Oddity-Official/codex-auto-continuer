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

- Final native gate: 163 passed, no skips/warnings, 43.70s; compileall and 0.3.0 version smoke passed. Explicit interpreter selection was exercised.
- Fresh self-contained 96-file source export: new venv installation, 163 tests in 54.69s, portable build, wheel build and frozen UX probe passed without a parent checkout or existing installation.
- Frozen probe: isolated controls, no clients, one-second polling; implicit defaults, Continue, scan feedback, exclusive once, same-PID reload and settings/prompt pause/repair, graceful stop; zero Codex connections and zero user-chat dispatches.
- Initial privacy inventory: all five existing commits, 171 distinct blobs, working tree, portable ZIP and wheel; no credential/profile/project-path matches, runtime files or private author emails. Pre-delivery scanning includes updated source and the source handoff.
- Deep frozen inspection: both executable CArchives/PYZ archives, nested stdlib ZIP and 440 bytecode modules/code filenames; no personal build paths found.
- Actual deployed 521 release hashes, wheel source/asset parity, licenses/source and repository Markdown file targets pass. Current portable bytes are unchanged; wheel README metadata is refreshed.
- Audit cleanup reports zero deletions. No production monitor was restarted or live user chat resumed during this audit.
- GitHub-hosted CI, natural quota-reset delivery, actual VS Code UI delivery, fresh login, manual visual/accessibility review and other Windows installations remain unobserved. EXEs are unsigned and queue concurrency/idempotency limits remain documented.
- Five failed system-temp socket fixtures remain outside the repo because the host rejected their exact scoped cleanup. Successful fresh staging/fixtures clean up normally and no failed fixture is in an artifact.

Exact settings, commands and limits are in Docs/VALIDATION.md and the dated publication audit.

## Artifacts

Portable: `dist/codex-auto-continuer-0.3.0-windows-x86_64.zip`, SHA-256 `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`.

Optional wheel: `dist/codex_auto_continuer-0.3.0-py3-none-any.whl`, SHA-256 `ff24973657c9482d457a5cb28319b49b07df447f848dd5c328014e6ff66076e1`.

Stable source transport: `codex-auto-continuer-codex-handoff.zip`. It includes useful public development records and audit state with per-file hashes and Git provenance, excluding runtime data, App, dependencies, build output and secrets. Packaging runs retention and transport validation.
