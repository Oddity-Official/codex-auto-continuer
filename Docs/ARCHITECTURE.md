# Architecture

## Runtime and controls

The supervisor is a per-user Python 3.13 process. Its recovery engine uses the standard library. The Windows tray uses pystray and Pillow. PyInstaller packages GUI and console EXEs sharing an adjacent `_internal` folder.

The GUI entry point defaults to `tray`. A tray instance starts a hidden supervisor, polls a small local status snapshot every 2 seconds, and sends serialized control commands through the companion console EXE. Commands have 90-second bounds, or 120 seconds for one-cycle controls. Timed-out process trees are stopped. The tray does not poll Codex independently for its icon status.

Both interfaces call the same CLI implementation. The menu has start, stop, restart, scan, one cycle, settings, Markdown prompt, logs, initialization, scope, privacy and login controls. Prompt edits apply at the next send. Other manual settings edits require restart.

## Codex control path

1. Find the native Codex executable from explicit configuration, PATH, the standard Desktop location or recognized npm vendor layout. Never execute an arbitrary shell launcher.
2. Require CLI version 0.160.0 or newer. Probe the daemon version; optionally start it.
3. Connect to its private Unix-domain control socket and perform WebSocket initialization. On Windows, a standard-library ctypes bridge marshals Winsock's Unix-domain address. Python owns all socket I/O; paths must fit 107 UTF-8 bytes.
4. Read account limits and paginated thread metadata. Discovery uses descending update time, but eligibility uses the failed turn's completion time.
5. Read the latest turn with `itemsView = notLoaded`. Record only `failed / usageLimitExceeded` within the 24-hour window. Never cache by second-granularity thread timestamps.
6. Persist the exact thread/turn obligation before dispatch.
7. Require `ordinaryUsageAllowed == true`, then revalidate the exact thread and latest failed turn.
8. For `notLoaded`, resume and verify the exact returned thread ID. Accept only the verified -32600 active-writer error naming this exact thread as evidence of a separate owner.
9. Re-read the exact thread/turn and quota after ownership handling. Read the current Markdown prompt, validate it and log only its hash and length.
10. Save dispatch intent before `thread/queue/add`. Require the returned queue ID and matching deterministic client message ID.
11. Reconcile the queue and latest turn on later cycles. Close each connection before sleeping, so a resume subscription cannot become a sleeping approval/input subscriber.

No UI automation or model-switching path exists. Each RPC has a total deadline that notifications, pings and fragmented frames cannot extend.

## Thread scope

Default `allInteractive` accepts CLI and VS Code sources plus configured Desktop custom sources, initially chatgpt and atlas. It excludes exec, appServer, unknown and subAgent sources. Desktop-only mode accepts vscode only with a configured Desktop originator, initially Codex Desktop, or those configured custom sources.

All visible sessions must share the same native Codex home and account. This is not a cross-host or cloud monitor.

Discovery uses `scan_lookback_hours`, default 24. Recorded obligations age independently and are revalidated by exact metadata reads. A quota failure without completion time is a protocol error, not permission to guess recency.

## Durable state

State schema version 2 stores obligations and delivery observations. An obligation contains exact thread/failed-turn IDs, detection time, advisory reset time, deterministic client message ID, phase-change time and any known queue ID. Only one obligation per thread is permitted.

```text
pending -> dispatching -> submitted
                 \-> uncertain
```

`dispatching` is synced before the queue RPC. A lost response makes the send uncertain. Restart reconciliation looks for an advanced turn or the exact client message ID in the queue. It never assumes that a client message ID makes queue addition idempotent. An unresolved ambiguous send stops after the recovery interval.

Submitted deliveries also create durable observations. These survive removal of a stale obligation and process restart, allowing later metadata to record a subsequent completed, failed or interrupted turn. Live active status takes precedence over an apparently terminal persisted history entry.

A subsequent turn is not proof that our message caused it: a user can advance the chat concurrently. Telemetry labels it `delivery.subsequent_turn`, not guaranteed delivery success. Missing or archived chats end observations.

State writes flush and sync a temporary file before atomic replacement. Invalid versions, identities, duplicate records or queue ownership fail closed. Schema changes are deliberate, not silent data-loss migrations.

## Stale cancellation and quota policy

Manual progress, active work, missing chats, archive or scope changes invalidate pending obligations. If a send may already have happened, enumerate that exact thread's queue and delete only entries carrying our deterministic client message ID. Verify their removal before forgetting the obligation. Unrelated queue entries remain untouched.

The verified API has no compare-and-swap precondition against a turn revision. A narrow race remains between final revalidation and queue acceptance. We minimize it and remove observable stale queued work, without claiming unavailable atomicity.

Reset timestamps and percentages never authorize dispatch. Exhausted-window resets are only sleep hints and diagnostics. Dispatch runs oldest-first, with another account-permission read between chats.

The supervisor never answers approvals, security prompts, tool elicitations or user-input requests. Active threads are not eligible for new obligations.

## Data location and single instance

Portable EXEs use adjacent `data`; source checkouts use `.data/runtime`. Explicit config paths put state, prompt and logs beside that config. Pip installations default to the per-user directory, or attach to the last registered app's absolute config path. A moved/missing registered config fails clearly instead of guessing.

Small global control files remain under the per-user state directory: supervisor/tray OS locks, stop and scan requests, and the owner record. Locks prevent concurrent copies from dispatching or creating duplicate tray icons. They are not stale PID assertions.

The supervisor takes its OS lock before loading state and initializing telemetry. A conflicting command cannot overwrite an active runtime snapshot. `start` checks the owner, launches a hidden process and waits up to 10 seconds for its lock. `stop` waits up to 60 seconds for the current cycle to finish. Sleep/reconnect waits check stop/scan requests every second.

A description-owned native Startup shortcut targets the GUI EXE, or pythonw for a source install, with an absolute config path and no batch shell. Windows Shell creates it through bounded PowerShell. It refuses unmanaged or link/reparse targets. Moving a deployment requires reinstalling the shortcut.

## Local telemetry

The supervisor writes `telemetry.jsonl`; the tray writes `tray.jsonl`. Separate streams prevent multiprocess log rotation races. Schema 1 events carry UTC timestamp, PID, application version, privacy mode, event name and structured metadata.

RPC summaries are allowlisted, never raw payload dumps. Errors retain classes, numeric RPC codes, timings and stack module/function/line locations. Detailed mode enables actual identifiers, names and paths, not arbitrary exception text or conversation content.

Private mode omits personal metadata and uses HMAC-SHA256 keyed pseudonyms for thread, turn and queue IDs. The key persists locally for correlation. State still needs real identifiers; privacy applies to telemetry, not the whole data folder. Files are not encrypted.

Rotation defaults to 16 MiB and 8 backups per stream. A privacy change reconfigures the tray stream and restarts the supervisor; old logs remain unchanged. I/O failures stop rather than silently discard diagnostics.

Runtime status records phase, PID, cycle counts, quota permission, update time and error class. It supports the tray without storing conversation bodies. Build and handoff tools exclude runtime files, secrets, caches and the deployed App directory.
