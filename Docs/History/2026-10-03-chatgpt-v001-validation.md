# Verification

## Current scope

This checkpoint contains the first application implementation: Python runtime, direct shared app-server transport, supervisor/state machine, CLI, Windows Startup integration, tests and packaging metadata.

## ChatGPT/Linux checks

Environment: disposable Linux sandbox, Python 3.13.5. Linux validates portable logic and the AF_UNIX/WebSocket implementation available on this host; it is **not** proof of native Windows behavior.

Full project regression:

```text
python3 -m pytest tests scripts/tests -q
```

Result: **101 passed, 2 skipped**. The two skips are the pre-existing native-Windows PowerShell workflow-wrapper tests.

Bytecode compilation:

```text
python3 -m compileall -q src tests scripts
```

Result: **passed**.

Packaging/install smoke:

```text
python3 -m pip install --no-deps --no-build-isolation --target /tmp/cac-installed .
PYTHONPATH=/tmp/cac-installed python3 -m codex_auto_continuer --version
PYTHONPATH=/tmp/cac-installed python3 -m codex_auto_continuer config-path
```

Result: wheel built and installed successfully; CLI reported version `0.1.0` and resolved its per-user config path.

A source scan found no `TODO`, `FIXME`, or `XXX` markers under `src/` or `tests/`.

## Covered regression areas

- exact `usageLimitExceeded` turn classification versus unrelated failures
- no dispatch when `ordinaryUsageAllowed` is false or null
- stale/manual progress revalidation before continuation
- deletion of this tool's exact stale queued submission while preserving unrelated queue entries
- sequential multiple-thread dispatch with rate-limit recheck between threads
- unloaded-thread `thread/resume` path and subscription tracking
- fail-loud ambiguous post-crash dispatch reconciliation
- transient latest-turn read recovery without suppressing later detection
- Desktop-only and all-interactive source scoping
- unknown protocol status/source rejection
- corrupt/invalid durable state rejection
- per-user single-instance locking (portable POSIX path tested here)
- WebSocket handshake validation, prefetched frames, fragmentation, ping/pong, masking and binary-message rejection
- JSON-RPC notification/server-request handling without auto-answering approvals
- queue pagination and queue deletion response validation
- config validation and managed Startup-file ownership behavior

## Native Windows gate

Run from native PowerShell 7:

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
```

The gate runs application + workflow tests and compiles the application source with the configured Python 3.13 launcher.

**Not run here:** native Windows gate, Windows `msvcrt` lock behavior, Windows AF_UNIX connection to a real Codex daemon, real Codex Desktop coexistence, and real reset-to-continuation flow. These remain explicitly unverified rather than inferred from Linux.
