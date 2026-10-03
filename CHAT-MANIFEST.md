# ChatGPT manifest

Checkpoint: v001

## ChatGPT work

- Replaced the scaffold-only state with the first complete Python 3.13 product implementation.
- Added direct connection to Codex's shared app-server daemon over its private AF_UNIX WebSocket/JSON-RPC interface; no UI automation path exists.
- Added exact structured usage-limit detection and authoritative recovery gating on `ordinaryUsageAllowed == true`.
- Added durable exact-thread/exact-turn continuation obligations, deterministic client message IDs, atomic state writes, strict state validation, and fail-loud ambiguous-dispatch recovery.
- Added unloaded-thread `thread/resume`, queue add/list/delete handling, stale queued-continuation deletion, multiple-thread sequential dispatch with per-dispatch rate-limit recheck, and configurable continuation prompt.
- Added short-lived resume subscriptions that never answer approvals or explicit user-input requests.
- Added cross-process single-instance locking and marker-owned per-user Windows Startup integration.
- Added package/CLI metadata, architecture/research/validation documentation, and updated the native Windows verification gate.
- Preserved `CODEX-MANIFEST.md` as Codex-owned state based on `local-bootstrap`.

## Verification

ChatGPT/Linux (Python 3.13.5):

- `python3 -m pytest tests scripts/tests -q`: **101 passed, 2 skipped**. The two skips are intentionally native-Windows PowerShell-wrapper tests.
- `python3 -m compileall -q src tests scripts`: passed.
- `python3 -m pip install --no-deps --no-build-isolation --target /tmp/cac-installed .`: wheel built and installed successfully.
- Installed smoke: `python3 -m codex_auto_continuer --version` reported `0.1.0`; `config-path` executed successfully.
- Markdown relative-link audit and required-workflow-anchor audit: passed.
- `src/` + `tests/` scan for `TODO` / `FIXME` / `XXX`: clean.

Native Windows verification and live Codex Desktop reset/continuation scenarios remain explicitly pending; Linux results are not claimed as evidence for those platform-specific paths.
