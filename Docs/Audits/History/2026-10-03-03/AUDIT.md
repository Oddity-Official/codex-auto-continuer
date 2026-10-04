# Codex Auto Continuer audit

Audit date: 2026-10-03
Started at: 2026-10-04T06:38:44.853180+00:00

Completed verification: 4 October 2026, user timezone. The audit began on 3 October and crossed local midnight. Reviewed source: `f8abd3c`, application 0.3.0, plus the publication changes described below. No production code or running deployment was changed.

## Scope and decision

The user chose one public Git repository. Sanitized audit records and ChatGPT/Codex manifests stay tracked and public. Binary releases contain only the app, runtime, short guide, licenses, corresponding tray source and checksums. No separate publication checkout, history rewrite, remote creation or upload was performed.

Reviewed: every existing reachable commit/blob; current public files; portable and wheel contents; compressed executable/Python archives; author metadata; Git/source-export exclusions; contributor setup; build workflow; public docs; retained native UX/safety tests; and a fresh self-contained source export.

## Confirmed findings and fixes

| Priority | Finding | Reproduction and disposition |
| --- | --- | --- |
| Medium | Source exports could include root portable data, root runtime settings/prompt/state and `.env.*` files | A synthetic export containing `data/state.json`, `data/telemetry.jsonl`, root settings/prompt, a numbered gzip log backup, `.env.local` and nested `.env.production` retained the private canary before repair. Project exclusions now cover portable/root data; the exporter rejects environment variants and root log streams/backups. Regression passes and source bytes remain unchanged. |
| Medium | Git ignore rules did not cover the same supported local files | NUL-delimited `git check-ignore --stdin` regression verifies root portable/runtime and environment variants are ignored, while public source/docs remain trackable. No such private data was present in existing history. |
| Low | Documented venv setup did not satisfy the Windows gate | The gate unconditionally selected the global launcher. It now prefers the venv, supports explicit `-PythonPath`, checks the required Python version and prints its selection. A fresh isolated setup passes without global dependency installation. |
| Low | A stale imported checksum manifest looked like a current release checksum | `_CHECKPOINT_MANIFEST.json` described v001, not current source. It was already excluded from transport and was not an anchor. Removed from the current tree; bootstrap commit `643ba04` preserves the verified import and its checksum record. ChatGPT's manifest is unchanged. |
| Low | Public docs mixed everyday use and local workflow details | README is shortened; contributor setup/build and safe diagnostic sharing have clear entry points. Docs index separates usage/technical owners from development records. Previous verification is dated in history rather than overwritten. The comparison remains in README as requested. |
| Low | Audit rotation left live Markdown targets pointing at the previous current folder | Research and historical verification links now resolve to the archived audit. Dated results were not rewritten as current observations. |

No critical production defect or private-data leak was confirmed in the reviewed repository/artifacts.

## Privacy inventory

At the reviewed baseline, all five commits and 171 distinct Git blobs were inspected. Findings: zero credential-shaped values, zero real local profile/project path matches, zero runtime files, zero private author emails. Git authors use the account's intended public GitHub no-reply identity. Working-tree files are scanned separately after edits.

The portable ZIP has 522 entries, including its manifest. Inspection decompresses both EXE CArchives/PYZ archives and nested `base_library.zip`, scans 440 bytecode modules and recursively checks their code filenames. It also checks uncompressed entry content and UTF-8/UTF-16 local path markers. Findings: zero credential/profile/project-path matches. Wheel: 30 entries, likewise clean.

The probe reports categories, locations and fingerprints, never matched credential values. Its targeted patterns are not a universal secret detector. Manual review of records and metadata supplements the scan. Runtime settings, prompt, logs, state and correlation key were not copied into evidence. The used App remains ignored.

## Environment and exact checks

Windows 11 build 10.0.26300 x86_64; PowerShell 7.6.6; CPython 3.13.7. Venv runtime: pystray 0.19.5, Pillow 12.3.0, TOMLKit 0.15.1, six 1.17.0. Fresh build: pytest 9.1.1, setuptools 84.0.0, PyInstaller 6.22.3, hooks 2026.8, resvg-py 0.5.0. Native Codex CLI/daemon baseline: 0.160.0.

| Check | Exact scope/bounds | Result |
| --- | --- | --- |
| Privacy regressions | Two synthetic source-export/Git-ignore checks, outer 40s | Source-export canary failed before repair; both pass after repair |
| Workflow suite | `scripts/tests/test_project_workflow.py`, outer 80s | 28 passed, 29.96s |
| Native socket focused checks | `tests/test_ws_unix.py` and `tests/test_appserver.py`, outer 40s | 14 passed, 0.13s after fixture repair; two focused real handshake checks also pass globally |
| Current native gate | pytest 180s; compileall 120s; interpreter/version checks 30s; outer 360s | Initial 163 passed in 46.98s; final explicit-interpreter gate 163 passed in 43.70s; no skips/warnings; compilation/version passed |
| Fresh source setup | 96 source files through transport exclusions, no existing venv/Git/App/data; venv 60s, install 180s | Fresh `.[dev,build]` setup passed |
| Fresh native gate | Same native gate, outer 300s | 163 passed, no skips/warnings, 54.69s; compilation/version passed |
| Fresh build and wheel | Native builder 360s, internal PyInstaller 300s; wheel 120s | Both passed; clean runtime boundary, 521 manifest file hashes and CRC verified |
| Fresh frozen UX | Own directory with spaces/percent; no clients; 1s poll; isolated per-user controls; commands 20s, stop 65s, waits 15s, outer 150s | Implicit defaults, Continue, exclusive once, correlated scan, same-PID reload/pause/repair and graceful stop passed; zero Codex connections/dispatches |
| Actual artifacts | Wheel/source parity, deployed 521 hashes, repository Markdown targets; outer 40s | Passed; current portable unchanged; wheel README metadata refreshed |
| Deep publication scan | History, working tree, release archives; Git calls 20s each, outer 120s | No matches or broken Markdown file links before delivery |

The first venv gate reported two failures and two teardown errors: temporary native listeners in this host's system temp directory could not be connected (Winsock 10022) or removed (1920). Global Python worked there. Resolving short paths did not fix it. Both interpreters pass with short checkout-local fixtures, and the venv connects successfully to the real Codex daemon. This isolates the observed failure to test socket creation/location; its exact host/Windows cause is not established. Production socket code is unchanged.

The five failed socket fixtures are outside the repository and release boundary. Cleanup was preflighted against exact owned paths and contents, but the host rejected the deletion command. No alternative deletion mechanism was attempted. Clean-source staging and successful fixtures clean up normally.

## Rerun

Run from the checkout root:

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-03-03/probe_publication.py') -TimeoutSeconds 120
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-03-03/probe_clean_source.py') -TimeoutSeconds 600
```

The clean-source probe installs dependencies over the network into an owned temporary venv, runs real Win32 test windows only, builds and exercises an isolated frozen app, then removes its staging directory. It does not launch another production monitor or send messages to user chats.

## CI and publication

Windows CI is included for pushes, pull requests and manual dispatch. Repository permissions are read-only; checkout credentials are not persisted; official actions are pinned to full commit hashes. Installation/build steps are bounded, and only named ZIP/wheel outputs are uploaded as short-lived CI artifacts. No secrets, Codex account or release-publishing permission is required.

Action references were verified against the official repositories: [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python), [upload-artifact](https://github.com/actions/upload-artifact). They are build dependencies, not bundled runtime telemetry. [GitHub's sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) explains why deleting a tracked file alone would not remove historical exposure. No such rewrite was needed for the inspected history.

Portable ZIP: 16,299,281 bytes; SHA-256 `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`. Wheel: 72,538 bytes; SHA-256 `ff24973657c9482d457a5cb28319b49b07df447f848dd5c328014e6ff66076e1`. The application remains 0.3.0: no runtime behavior changed and no live deployment replacement was necessary.

## Limits

The clean build is a new source/venv on this host, not another Windows installation or a GitHub-hosted execution. The workflow has not run on GitHub and no remote is configured. EXEs are unsigned. Prior real CLI/Desktop queue evidence remains applicable; actual VS Code UI delivery, natural account-reset automatic continuation and fresh login remain unobserved. The experimental queue's concurrent-progress/idempotency limitations remain documented. Native dialog/highlight regressions do not constitute manual visual/accessibility testing.
