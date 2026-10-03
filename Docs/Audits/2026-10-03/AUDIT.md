# Codex Auto Continuer native readiness audit

Audit date: 3 October 2026 (America/Los_Angeles).
Base: ChatGPT checkpoint v001; all 46 checksum entries verified before edits.
Bootstrap commit: `643ba04`.
Environment: Windows 11 10.0.26300 x86_64, PowerShell 7.6.6, Python 3.13.7, Codex CLI/daemon 0.160.0.

## Outcome

The confirmed native release blockers were repaired. The package is installed, its managed login shortcut is enabled and its hidden supervisor is running. Native regressions and controlled integration probes passed.

The production supervisor observed a real usage-limit failure and its waiting period. The user manually resumed before automatic dispatch, so it cancelled the stale obligation. Automatic continuation at natural recovery and a fresh Windows login remain unobserved. Do not label separate component checks as a natural automatic-reset observation.

## Confirmed findings and repairs

| Priority | Finding and minimal reproduction | Root cause and repair |
| --- | --- | --- |
| P0 | Initial Windows gate: 1 failed, 100 passed, 2 skipped. `socket.AF_UNIX` raised AttributeError | Standard Windows CPython lacks Unix path marshalling. Added Winsock family-1 address bridge; Python still owns all socket I/O. Native socket tests now execute rather than skip |
| P1 | Live thread/list sample: 74 threads, all vscode with Codex Desktop originator. Original Desktop filter accepted zero | Source alone does not identify this Desktop installation. Accept the verified source/originator pair, exclude ordinary VS Code sessions |
| P1 | One thread owned by a separate native server: daemon read notLoaded; resume returned -32600 active writer | Runtime status is server-local. Match only the verified exact-thread writer condition and send through the shared queue. Other errors stop |
| P1 | Active/completed-to-failed transitions sharing updatedAt could be missed | Removed second-granularity timestamp cache. Read the latest no-items turn for every recent eligible inactive thread |
| P1 | Recently touched metadata could revive an old quota failure; original default was 168 hours | User selected 24 hours. Check failed turn completedAt as well as metadata discovery. Keep already-recorded obligations past lookback |
| P1 | Quota or manual progress could change during thread/resume | Re-read exact thread/turn and authoritative permission immediately before queue add |
| P1 | A failed deletion could be forgotten; state could claim an unrelated client ID | Re-list after stale deletion before forgetting. Require deterministic client ID matching exact thread/turn |
| P1 | State was loaded before acquiring the instance lock | Lock before state load, preventing stale startup snapshots. Flush/fsync temporary state before atomic replace |
| P1 | Socket inactivity timeout did not bound RPCs with continuous notifications | Total monotonic RPC deadline also covers notifications, ping frames and fragmented payload reads. Initialization failure closes the client |
| P2 | Batch Startup paths were relative/shell-expanded and could show a console | Native description-owned .lnk directly targets pythonw with absolute config. No batch shell; refuse unmanaged/reparse targets |
| P2 | Background operation lacked graceful controls and bounded log size | Added start/stop/status lock checks, one-second stop checks during sleep, 2 MiB log rotation with 2 backups and body-free RPC diagnostics |

Relevant source locations: `src/codex_auto_continuer/uds.py`, `ws_unix.py`, `appserver.py`, `supervisor.py`, `state.py`, `instance_lock.py`, `startup.py`, `cli.py`, `config.py`, `codex.py`.

## Native probe results

### Read-only daemon

`probe_live.py`: CLI deadline 10s, RPC 5s, page limit 100, at most 12 latest-turn reads, outer deadline 90s. Observed daemon status running, version 0.160.0, successful initialize and quota read, 74 vscode/Codex Desktop threads, ordinaryUsageAllowed true.

Reads used no-items turn view. No conversation bodies were saved. A read-only SQLite metadata check independently confirmed the source classification; it did not modify Codex state.

### Separate owner

`probe_coexistence.py`: private stdio app-server and existing daemon, one owned read-only gpt-6-luna thread, fixed CAC_NATIVE_OK response, no tools. Request bound 12s, each completion wait 35s, daemon socket 5s, outer bound 100s.

Essential result:

```json
{
  "initialTurn": {"status": "completed", "errorInfo": null},
  "daemonReadStatus": {"type": "notLoaded"},
  "daemonError": {"code": -32600, "message": "thread <exact-thread-id> already has an active writer"},
  "queuedIdReturned": true,
  "queueTurnOnOriginalOwner": {"status": "completed", "errorInfo": null}
}
```

An empty thread without its first turn initially had no persisted metadata, so that initial empty-thread probe could not establish ownership. The completed-turn probe above did. Probe processes were stopped and owned threads archived.

### Unloaded queue and detached continuation

`probe_unloaded.py`: existing daemon, one owned read-only gpt-6-luna thread, fixed response, no tools; archive/unarchive to unload; 2 probe queue entries. RPC 5s, completion wait 35s, unload wait 5s, outer bound 110s.

Essential result:

```json
{
  "unloadedQueueCrud": "passed",
  "unrelatedItemPreserved": true,
  "unloadedResume": "passed",
  "detachedQueuedTurn": "completed"
}
```

Diagnostic refinements: immediate history read after turn/start preceded rollout initialization; the probe waits for completion. Unsubscribe did not unload the thread, so owned archive/unarchive supplies an actual unloaded state. Persisted history initially showed interrupted during a live active turn; the probe now also checks runtime status. With that correction, the detached queued turn completed.

### Native usage error

`probe_quota_serialization.py`: temporary isolated CODEX_HOME, localhost HTTP server returns 429 with usage_limit_reached, pro plan and advisory reset one hour ahead. Non-secret fixture key; no real account request. Connect wait 10s, RPC 2s, turn wait 20s, outer bound 60s.

Essential result:

```json
{
  "liveStatus": "failed",
  "liveErrorInfo": "usageLimitExceeded",
  "persistedStatus": "failed",
  "persistedErrorInfo": "usageLimitExceeded",
  "completedAtPresent": true
}
```

Initial custom socket parent failed Codex's private-directory preflight. Using Codex's default control directory in the isolated home let Codex create its protected directory. The probe process, fixture server and temporary home were cleaned up.

### Installed controls and login shortcut

`probe_installation.py`: installed site-packages module, start/once bounds 15s, status 45s, stop 65s, outer bound 120s. Running status true, second start idempotent, competing once exited 2 with instance-lock diagnostic, graceful stop passed, stopped status false.

The managed .lnk was then launched with Windows Shell, and background running status verified. No existing user thread was dispatched during activation: the foreground once cycle scanned 3 recent Desktop threads, detected 0 and dispatched 0.

### Real production quota observation

After activation, this Desktop chat stopped on a real quota failure. The installed process recorded the exact failed turn and waited through 9 scans with pending=1 and usageAllowed=False. The user then sent Continue. The next relevant cycle verified a different latest turn, cancelled the old obligation, and reported usageAllowed=True. It sent no automatic message.

Sanitized essential log records, in order:

```text
Recorded usage-limit obligation thread=<current-thread> turn=<failed-turn>
cycle scanned=3 detected=1 cancelled=0 dispatched=0 pending=1 usageAllowed=False
8 further scans: detected=0 cancelled=0 dispatched=0 pending=1 usageAllowed=False
Cancelling stale obligation thread=<current-thread> failedTurn=<failed-turn> latest=<manual-resume-turn>
cycle scanned=3 detected=0 cancelled=1 dispatched=0 pending=0 usageAllowed=True
```

The runtime state subsequently contained zero obligations, and OS-lock status remained running. This verifies real failure discovery, waiting and manual-progress cancellation. It does not establish why availability recovered or exercise natural automatic dispatch. Original per-user runtime logs remain outside the source transport; no conversation bodies were copied into this report.

## Standard verification

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
```

119 passed, no skips, 31.78 seconds; compileall and version smoke passed. Gate bounds: pytest 180s, compileall 120s, import/version 30s.

```powershell
py -3.13 -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
py -3.13 -m pip install --no-deps --force-reinstall dist/codex_auto_continuer-0.1.0-py3-none-any.whl
```

Build bound 90s, install bound 60s. Wheel build/install passed; installed version 0.1.0. The native console command resolves from Python 3.13 Scripts.

Final artifact inspection matched all 13 runtime modules byte-for-byte against the wheel and checked version, Python requirement and runtime dependency metadata. Wheel SHA-256: `c8c6101f43103314125803bd58b687d2cd5f97e53a9c0b254b44cdc9a7b235dc`. Markdown file targets and diff whitespace checks passed. The installed background instance remained running with no pending obligations.

## Rerun and limits

Use `scripts/run-project-command.ps1` with the exact outer bounds above. Live delivery probes make small real model requests on owned test threads. The installation probe stops the supervisor; restart it afterward. Quota serialization stays local and isolated.

Default production settings: 24-hour discovery; Desktop scope; 30s polls; 12s total RPC deadline; 20s Codex command timeout; 2s spacing; 5s reconnect backoff; 15s ambiguous-send recovery interval; daemon autostart enabled.

The API has no verified queue-add idempotency or turn-revision compare-and-swap contract. The runtime revalidates and reconciles, but cannot promise atomic dispatch versus manual progress. Automatic dispatch at natural recovery and two real simultaneously quota-stalled threads remain unobserved. Unsupported interface drift remains fatal. Current owner documents describe behavior; this dated report preserves the observations.
