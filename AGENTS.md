# Codex Auto Continuer agent instructions

## Project-specific contract

- Read `Docs/PRODUCT.md` for behavior, `Docs/ARCHITECTURE.md` for boundaries, `Docs/RESEARCH.md` for upstream assumptions and `Docs/VALIDATION.md` for affected checks. Do not reread unrelated contracts for prose-only changes.
- Default scope includes interactive CLI, VS Code and Desktop, never executor or sub-agent sessions. Desktop-only scope checks originator as well as source: this installation uses `vscode` with originator `Codex Desktop`.
- The daemon and Desktop can be separate app-server owners. Handle only the verified exact-thread active-writer error by using the shared queue; never treat unrelated resume errors as successful ownership detection.
- Discovery defaults to the last 24 hours of failed-turn completion time. Recorded obligations remain durable beyond that window.
- Target native Windows 11 x86_64 and local interactive Codex clients. Source development uses PowerShell 7 and Python 3.13; portable users need neither. Prefer first-party CLI/app-server/thread interfaces. UI automation, clipboard injection, focus stealing and screen scraping are not acceptable fallbacks.
- Runtime code is under `src/codex_auto_continuer/`. The Windows tray uses pystray and Pillow; TOMLKit preserves settings comments. Recovery uses the standard library. `pytest` and the SVG renderer are development/build-only. Build portable releases in `.venv` using `scripts/build-portable.ps1`, not over a running deployment.
- Keep the tray focused on everyday controls; diagnostic scan/once/restart/init commands remain in the CLI. Re-read the saved Markdown prompt immediately before sending. Never substitute a default prompt for an invalid user file. Settings are annotated TOML overrides with validated cycle-boundary reload.
- Keep portable data beside the EXEs and source data in `.data/runtime`, but use shared per-user control locks. Never package runtime data, installed dependencies or the deployed `App` directory in a source handoff.
- Block diagnostically on unsupported identity, protocol drift or missing capabilities. Default Balanced mode permits schema-verified stable builds; Strict additionally requires exact certification. Isolate chat-local ambiguous dispatch without retrying while other safe chats continue. Never guess a thread or treat unrelated failures as quota stalls.
- `ordinaryUsageAllowed == true` is the dispatch authority. Do not infer recovery from reset timestamps or percentages.
- Protect conversation privacy: do not persist prompt/response bodies, credentials, raw RPC payloads or exception locals. Telemetry defaults to keyed IDs without names/paths; detailed mode explicitly retains real metadata. Durable state and delivery observations store IDs, times, dispatch phase and queue IDs.
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
- Apply the development/delivery tiers in `Docs/WORKFLOW.md`: focused checks during iteration; native gate and relevant integration checks for completed code changes; documentation checks for prose-only changes. At every completed delivery, including prose-only work, run audit cleanup, reconcile docs, update `CODEX-MANIFEST.md`, commit scoped changes when safe, and refresh `pwsh -File scripts/pack-codex-handoff.ps1`. Inspect status afterward and include managed retention changes if needed. Give the user the stable handoff path. Do not build releases or repeat full gates after each intermediate edit.
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
