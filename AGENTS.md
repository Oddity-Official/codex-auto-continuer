# Codex Auto Continuer agent instructions

## Project-specific contract

- Read `Docs/PRODUCT.md`, `Docs/ARCHITECTURE.md`, `Docs/RESEARCH.md`, and `Docs/VALIDATION.md` before changing product behavior.
- Desktop scope must check the verified originator as well as session source. This Windows install uses `vscode` with originator `Codex Desktop`; ordinary VS Code extension sessions must remain excluded.
- The daemon and Desktop can be separate app-server owners. Handle only the verified exact-thread active-writer error by using the shared queue; never treat unrelated resume errors as successful ownership detection.
- Discovery defaults to the last 24 hours of failed-turn completion time. Recorded obligations remain durable beyond that window.
- Target native Windows 11 / PowerShell 7 / Python 3.13 and Codex Desktop. Prefer Codex's first-party CLI/app-server/thread interfaces. UI automation, clipboard injection, focus stealing and screen scraping are not acceptable fallbacks because they destroy the purpose of the tool.
- Runtime code is under `src/codex_auto_continuer/` and has no third-party runtime dependencies. `pytest` is development-only.
- Fail fast and diagnostically on unsupported Codex versions, protocol drift, ambiguous dispatch state, or missing capabilities. Never silently continue a guessed thread or treat unrelated failures as quota stalls.
- `ordinaryUsageAllowed == true` is the dispatch authority. Do not infer recovery from reset timestamps or percentages.
- Protect conversation privacy: do not persist prompt/response bodies. Durable runtime state is limited to identifiers, timestamps, dispatch phase and queue IDs.
- Never auto-answer app-server approvals, security prompts, tool elicitations or explicit user-input requests. Keep resume subscriptions short-lived.
- Preserve exact-thread safety. If user/manual progress makes an obligation stale, remove any queue entry carrying this tool's deterministic client message ID before forgetting the obligation.
- Do not add an automatic retry for ambiguous queue submissions unless a verified Codex idempotency contract is found. Failing loud is preferable to duplicate work.
- The native Windows gate is `pwsh -NoProfile -File scripts/verify-windows.ps1`.

## ChatGPT environment

- Work in the disposable sandbox using the project's declared runtime and dependencies. Do not assume the user's native tools or source-project paths exist.
- Use fixture configuration for tests when host-specific paths are unavailable. Do not rewrite the user's central configuration to match the sandbox.
- Linux validation is useful, not proof of Windows compatibility. Do not require WSL or include installed runtimes, wheels/vendor trees, caches or build output in artifacts.
- Read both manifests and the current audit evidence on receipt of a Codex handoff. Account for local work before creating the next canonical checkpoint.
- Update `CHAT-MANIFEST.md`, assign a new monotonically increasing checkpoint ID, and run `python3 scripts/project-workflow.py checkpoint --id ID`. Persist the ZIP to the Library or another available durable attachment. Never overwrite or reuse a checkpoint ID. Do not run the Codex handoff packer for normal ChatGPT work.

## Codex environment

- Work in native Windows with PowerShell 7 and Python 3.13. Do not use WSL or sandbox-only toolchain bundles.
- Preview incoming canonical checkpoints with `pwsh -File scripts/import-checkpoint.ps1 -ArchivePath 'absolute-path.zip' -Preview`. Import only after the project subtree is clean and the preview is understood. Unrelated sibling changes need not be cleared.
- The importer verifies archive paths, role, project anchors and hashes, preserves runtime data and unowned files, and creates a recovery backup outside the checkout. Keep that backup until native verification succeeds. After import, verify before committing; the importer resets the Codex record to the new base with verification marked pending.
- After every completed project modification, run audit cleanup, applicable tests and the native gate, reconcile documentation, update `CODEX-MANIFEST.md`, commit scoped changes when safe, then refresh `pwsh -File scripts/pack-codex-handoff.ps1`. Inspect project status afterward; if packaging pruned tracked audit data, commit those managed changes and refresh again. Give the user the stable `codex-auto-continuer-codex-handoff.zip` path. Never make the user ZIP source manually.
- Do not rewrite `CHAT-MANIFEST.md` for Codex work.

## Shared workflow

- Read `README.md`, `Docs/README.md` and `Docs/WORKFLOW.md` before substantial work. Keep product/source contracts in their owner documents and changing verification results in `Docs/VALIDATION.md`.
- Keep open work concise; move completed design, implementation and superseded verification records into `Docs/History/`. Index history once in `Docs/README.md`. Preserve historical observations; do not rewrite them to describe later code.
- Before a new audit, read `Docs/Audits/README.md` and run `scripts/manage-audits.py start --date YYYY-MM-DD` with the user's current date (`py -3` on Windows, `python3` on Linux). Receiving a handoff or implementing findings does not start a new audit.
- Keep `AUDIT.md`, all useful probes/scripts, fixtures and results together in the dated folder. Record provenance, settings, bounded commands, priorities and limits, and put minimal reproductions in the report itself. Helpers must be portable; compiler output and installed dependencies do not belong in evidence.
- Transport builders run retention automatically. Current audits stay intact. Archived supporting data expires after 7 days; archived reports older than one calendar month expire during monthly checks. Preserve ignored `.maintenance.json` in transports. Exclude locks and caches. Never bypass retention failures.
- Handoffs are stable source transports; ChatGPT checkpoints are never-overwritten canonical snapshots. `.project-workflow.json` owns project identity, anchors, native Python launcher selection and extra export exclusions. Exports must remain self-contained without a parent checkout.
- Protect unrelated changes and local runtime data. Bound processes from their first invocation, terminate children on timeout, and fail clearly rather than silently dropping source, evidence or errors. Use pytest for Python regressions and keep tests that cover real failure modes.
- Audit docs and code for contradictions, broken links and unsupported claims before delivery. Record failed or unavailable checks honestly.
