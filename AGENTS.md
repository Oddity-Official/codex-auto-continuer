# Codex Auto Continuer agent instructions

## Project-specific contract

- Read `Docs/PRODUCT.md` for behavior, `Docs/ARCHITECTURE.md` for boundaries, `Docs/RESEARCH.md` for upstream assumptions and `Docs/VALIDATION.md` for affected checks. Do not reread unrelated contracts for prose-only changes.
- Default scope includes interactive CLI, VS Code and Desktop, never executor or sub-agent sessions. Desktop-only scope checks originator as well as source: this installation uses `vscode` with originator `Codex Desktop`.
- The daemon and Desktop can be separate app-server owners. Handle only the verified exact-thread active-writer error by using the shared queue; never treat unrelated resume errors as successful ownership detection.
- Discovery defaults to the last 24 hours of failed-turn completion time. Recorded obligations remain durable beyond that window.
- Target native Windows 11 x86_64 and local interactive Codex clients. Source development uses PowerShell 7 and Python 3.13; portable users need neither. Prefer first-party CLI/app-server/thread interfaces. UI automation, clipboard injection, focus stealing and screen scraping are not acceptable fallbacks.
- Runtime code is under `src/codex_auto_continuer/`. The Windows tray uses pystray and Pillow; TOMLKit preserves settings comments. Recovery uses the standard library. `pytest` and the SVG renderer are development/build-only. Build portable releases in `.venv` using `scripts/build-portable.ps1`, not over a running deployment.
- Keep the tray focused on everyday controls; diagnostic scan/once/restart/init commands remain in the CLI. Re-read the saved Markdown prompt immediately before sending. Never substitute a default prompt for an invalid user file. Settings are annotated TOML overrides with validated cycle-boundary reload.
- Keep portable data beside the EXEs and source data in `.data/runtime`, but use shared per-user control locks. Never commit runtime data, installed dependencies or the deployed `App` directory.
- Block diagnostically on unsupported identity, protocol drift or missing capabilities. Default Balanced mode permits schema-verified stable builds; Strict additionally requires exact certification. Isolate chat-local ambiguous dispatch without retrying while other safe chats continue. Never guess a thread or treat unrelated failures as quota stalls.
- `ordinaryUsageAllowed == true` is the dispatch authority. Do not infer recovery from reset timestamps or percentages.
- Protect conversation privacy: no bodies, credentials, raw RPC payloads or exception locals in telemetry. The only input-persistence exception is opt-in owner-supported queue holding: account-bound DPAPI-encrypted canonical queued inputs, never whole conversation history, source exports or uploads. Telemetry defaults to keyed IDs without names/paths; detailed mode explicitly retains real metadata. Ordinary durable state and delivery observations store IDs, times, dispatch phase and queue IDs.
- Never auto-answer app-server approvals, security prompts, tool elicitations or explicit user-input requests. Ordinary resume subscriptions close between cycles. Optional holding observes only established active chats on the connected owner, disconnects on approval/input requests and never falls back to peer interception or blind replay. Stop/disable preserves private held inputs.
- Preserve exact-thread safety. If user/manual progress makes an obligation stale, remove any queue entry carrying this tool's deterministic client message ID before forgetting the obligation.
- Do not add an automatic retry for ambiguous queue submissions unless a verified Codex idempotency contract is found. Failing loud is preferable to duplicate work.
- The native Windows gate is `pwsh -NoProfile -File scripts/verify-windows.ps1`.

## Working practice

- Work in native Windows with PowerShell 7 and Python 3.13. Don't use WSL; Linux checks don't establish Windows behaviour.
- Read `README.md` and `Docs/README.md` before substantial work. Keep product and source contracts in their owner documents and current verification results in `Docs/VALIDATION.md`.
- Keep open work concise. Move completed design, implementation and superseded verification records into `Docs/History/`, indexed once in `Docs/README.md`. Preserve historical observations rather than rewriting them to describe later code.
- Protect unrelated changes and local runtime data. Bound processes from their first invocation, stop their children on timeout, and fail clearly rather than silently dropping source, evidence or errors. Use pytest for Python regressions and keep tests that cover real failure modes.
- Check docs and code for contradictions, broken links and unsupported claims before finishing. Record failed or unavailable checks honestly.
