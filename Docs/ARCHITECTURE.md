# Architecture

## Runtime and controls

The supervisor is a per-user Python 3.13 process. Its recovery engine uses the standard library; TOMLKit preserves settings comments. Cryptography verifies Ed25519 release signatures. The Windows tray uses pystray and Pillow. PyInstaller packages GUI and console EXEs sharing an adjacent `_internal` folder.

The GUI entry point defaults to `tray`. A tray instance starts a hidden supervisor, polls a small local status snapshot every second, and sends serialized state-changing commands through the companion console EXE. Commands have 90-second bounds, or 120 seconds for one-cycle controls. Timed-out process trees are stopped. The tray does not poll Codex independently for its icon status. File actions run directly on separate threads, bypassing both subprocess startup and the control queue.

The tray exposes local status, start/stop, independent client choices, Windows login, prompt, settings, data folder, privacy, defaults, updates, About and exit. Release downloads use a separate background thread, so they do not block monitoring controls or file actions. Installation joins the serialized control path after verification. [Updates](UPDATES.md) owns download and replacement details. Diagnostic scan/once/restart/init commands remain in the CLI. Scan requesters use an OS lock, an atomic request ID and a matching completion acknowledgement.

Settings are annotated TOML overrides in `settings.toml`. Missing settings use built-in defaults; opening settings creates a comment-only template. TOMLKit preserves existing comments on tray edits. Unique temporary writes flush, sync and atomically replace the file. Valid saved settings and prompts are checked before each cycle; sleep watches file signatures every second. Invalid settings or prompts close the connection and pause dispatch while preserving state, then recover automatically after repair. Empty client selection does not connect when there is no outstanding state; existing obligations still reconcile and delete only our stale queued work.

About, status and confirmation dialogs use a dedicated native UI thread and a hidden Windows STATIC owner, not the tray notification window. Menu callbacks enqueue dialogs and return before modal interaction. Duplicate dialogs are suppressed. Exit dismisses only dialogs owned by that thread. The native OK button, X and Escape are regression tested.

The SVG master uses an off-white stack with a darker outline and renders green, yellow and red runtime PNGs at build time. Pillow loads these without an SVG renderer dependency. Green includes waiting for quota; yellow covers stopped, starting, paused and reconnecting; red means a blocking error.

The Win32 tray adapter builds the native menu on the UI thread immediately before each right-click popup. Labels, checks and enabled states are snapshots for that opening. Background updates and selected-item callbacks never replace a tracked menu; changes appear on the next opening. This preserves Windows' native hover highlighting and selection. The adapter uses the pinned pystray 0.19.5 backend without modifying its bundled sources.

## Codex control path

1. Find the native Codex executable from explicit configuration, PATH, the standard Desktop location or recognized npm vendor layout. Never execute an arbitrary shell launcher.
2. Require CLI version 0.160.0 or newer, retaining its full prerelease/build suffix. Probe the daemon version; optionally start it. A minimum version is not dispatch certification.
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

Each fresh connection verifies the CLI, daemon lifecycle response, connected server's user-agent version and managed binary. The managed binary generates the experimental schema. CAC checks its consumer-specific contract and looks for an exact-version/build certificate. Balanced mode also permits matching unknown stable builds; Strict requires certification. Schema results cache only in memory by binary SHA-256 and full version; file identity changes invalidate them. Rechecks before resume, queue addition and deletion catch daemon updates during a cycle. [Compatibility](COMPATIBILITY.md) owns policy and identity limits.

An internal `-32603` error from the read-only `account/rateLimits/read` endpoint is unavailable evidence, not a fatal contract failure. Monitoring closes the connection, clears current usage permission and retries at the configured reconnect interval with backoff capped at the greater of 30 seconds or that interval. Pending state remains unchanged. Status retains last-scan metadata, actual pending count and the safe method/code with repair guidance. Authentication/request errors, missing methods, malformed responses and mutation errors are not converted into this retry path. Server error bodies remain excluded.

## Thread scope

Default `clients = ["vscode", "cli", "desktop"]` accepts all three interactive clients. CLI source wins over originator. Desktop accepts vscode with a configured Desktop originator, initially Codex Desktop, or configured custom sources, initially chatgpt and atlas. Other vscode sources are extension sessions. Any combination, including [], is valid. Exec, appServer, unknown and subAgent sources remain excluded.

All visible sessions must share the same native Codex home and account. This is not a cross-host or cloud monitor.

Discovery uses `scan_lookback_hours`, default 24. Recorded obligations age independently and are revalidated by exact metadata reads. A quota failure without completion time is a protocol error, not permission to guess recency.

## Durable state

State schema version 2 stores obligations and delivery observations. An obligation contains exact thread/failed-turn IDs, detection time, advisory reset time, deterministic client message ID, phase-change time and any known queue ID. Only one obligation per thread is permitted.

```text
pending -> dispatching -> submitted
                 \-> uncertain
```

`dispatching` is synced before the queue RPC. A lost response makes the send uncertain. Restart reconciliation looks for an advanced turn or the exact client message ID in the queue. It never assumes that a client message ID makes queue addition idempotent. After the recovery interval, unresolved ambiguity isolates that chat without retrying. Other safe chats continue. Status, local telemetry and one non-modal notice explain the isolation. Later observable progress can resolve it automatically.

Submitted deliveries also create durable observations. These survive removal of a stale obligation and process restart, allowing later metadata to record a subsequent completed, failed or interrupted turn. Live active status takes precedence over persisted history. A terminal status without a finite completion timestamp is incomplete evidence, especially for a separate writer; it does not end observation.

A subsequent turn is not proof that our message caused it: a user can advance the chat concurrently. Telemetry labels it `delivery.subsequent_turn`, not guaranteed delivery success. Missing or archived chats end observations.

State writes flush and sync a temporary file before atomic replacement. Invalid versions, identities, duplicate records or queue ownership fail closed. Schema changes are deliberate, not silent data-loss migrations.

## Stale cancellation and quota policy

Manual progress, active work, missing chats, archive or scope changes invalidate pending obligations. If a send may already have happened, enumerate that exact thread's queue and delete only entries carrying our deterministic client message ID. Verify their removal before forgetting the obligation. Unrelated queue entries remain untouched.

The verified API has no compare-and-swap precondition against a turn revision. A narrow race remains between final revalidation and queue acceptance. We minimize it and remove observable stale queued work, without claiming unavailable atomicity.

Queue deletion acknowledges storage removal, not cancellation of input already selected by another server owner. Native probes confirmed accepted peer deletions followed by consumption. The dispatch lock is process-local. Stale cleanup cannot undo an already-selected turn; future user-input holding must not infer safe replay from deletion acknowledgement or a single immediate history-absence check. [Queue interception evidence](Audits/2026-10-04-03/AUDIT.md) owns measured timing and transport limits.

Reset timestamps and percentages never authorize dispatch. Exhausted-window resets are only sleep hints and diagnostics. Dispatch runs oldest-first, with another account-permission read between chats.

The supervisor never answers approvals, security prompts, tool elicitations or user-input requests. Active threads are not eligible for new obligations.

## Data location and single instance

Portable EXEs use adjacent `data`; source checkouts use `.data/runtime`. Explicit settings paths put state, prompt and logs beside those settings. Pip installations default to the per-user directory, or attach to the last registered app's absolute settings path. Missing settings are valid; a moved/missing registered data folder fails clearly instead of guessing.

Small global control files remain under the per-user state directory: supervisor/tray OS locks, stop and scan requests, and the owner record. Locks prevent concurrent copies from dispatching or creating duplicate tray icons. They are not stale PID assertions.

The supervisor takes its OS lock before loading state and initializing telemetry. A conflicting command cannot overwrite an active runtime snapshot. `start` checks the owner, launches a hidden process and waits up to 10 seconds for its lock. `stop` waits up to 60 seconds for the current cycle to finish. Sleep/reconnect waits check stop/scan requests every second.

A description-owned native Startup shortcut targets the GUI EXE, or pythonw for a source install, with an absolute config path and no batch shell. Windows Shell creates it through bounded PowerShell. It refuses unmanaged or link/reparse targets. Moving a deployment requires reinstalling the shortcut.

## Local telemetry

The supervisor writes `telemetry.jsonl`; the tray writes `tray.jsonl`; update checks/replacement write `updates.jsonl`. The installer waits for its requesting CLI to exit before taking over that update stream. Separate streams prevent multiprocess rotation races. Schema 1 events carry UTC timestamp, PID, version, privacy mode, event name and metadata.

RPC summaries are allowlisted, never raw payload dumps. Errors retain classes, numeric RPC codes, timings and stack module/function/line locations. Detailed mode enables actual identifiers, names and paths, not arbitrary exception text or conversation content.

Private mode omits personal metadata and uses HMAC-SHA256 keyed pseudonyms for thread, turn and queue IDs. The key persists locally for correlation. State still needs real identifiers; privacy applies to telemetry, not the whole data folder. Files are not encrypted.

Routine RPC requests are suppressed unless `diagnostic_trace` is enabled. Responses contribute per-method counts, total and maximum duration to each cycle summary. Relevant discovery, quota and metadata events log only changes, with a bounded 4096-entry cache. Queue add/delete/resume, dispatch and error events remain explicit. Trace increases detail, not personal-data access; Private/Detailed remains a separate formatter policy.

Rotation defaults to 8 MiB and three gzip backups per stream. Compression completes and atomically installs the backup before removing the original. Privacy changes reconfigure each stream on validated reload without restarting the supervisor; old logs remain unchanged. Telemetry I/O failure stops dispatch and reports a blocking local snapshot when writable. Repair dialogs and exit remain usable if their own logging destination fails.

Runtime status records phase, PID, cycle counts, quota permission, update time and error class. It supports the tray without storing conversation bodies. Build and handoff tools exclude runtime files, secrets, caches and the deployed App directory.
