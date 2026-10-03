# Architecture

## Runtime

The product runtime is Python 3.13 with no third-party runtime dependencies. `pytest` is development-only. The supervisor is a per-user process intended to run on native Windows 11.

## Control path

1. Resolve `codex` from `PATH` and require CLI version 0.160.0 or newer.
2. Probe the first-party local app-server daemon with `codex app-server daemon version`; optionally start it with `codex app-server daemon start`.
3. Connect to the private Unix-domain control socket and perform WebSocket `initialize` / `initialized`. On Windows, a small standard-library `ctypes` bridge marshals the Winsock `sockaddr_un` address. Python owns the socket and all I/O. Socket paths must fit in 107 UTF-8 bytes.
4. Poll `account/rateLimits/read` and `thread/list` through JSON-RPC.
5. For in-scope threads updated within the 24-hour discovery window, read the newest turn with `itemsView = notLoaded`. Record an obligation only for `failed / usageLimitExceeded` with a completion timestamp inside that window. Do not cache by second-granularity thread timestamps: a new turn can share the previous turn's timestamp.
6. Persist that obligation before attempting any continuation.
7. Dispatch only when `ordinaryUsageAllowed` is explicitly `true`.
8. Immediately re-read the exact thread and turn. Any user/manual progress cancels the stale obligation.
9. If the daemon reports `notLoaded`, try `thread/resume` and verify the exact returned thread ID. If that method returns the verified `-32600` active-writer error for this exact thread, another Codex server owns it. Queue to that owner through the shared queue. Never steal its lock. All unrelated resume errors remain fatal. The connection closes after the cycle so this supervisor cannot remain a sleeping approval/input subscriber.
10. Submit the configured continuation through `thread/queue/add` using a deterministic `clientUserMessageId` derived from the exact thread/failed-turn pair.
11. On subsequent cycles, reconcile the durable obligation against the latest turn and `thread/queue/list` before doing anything else.

No UI automation path exists.

## Thread scope

The default `thread_scope = "desktop"` accepts `source = vscode` only when its originator matches `desktop_originators`, initially `Codex Desktop`. It also accepts configured custom sources, initially `chatgpt` and `atlas`. `allInteractive` additionally accepts CLI and all VS Code sessions, but never arbitrary custom, executor, app-server, sub-agent or unknown sources.

Discovery uses `scan_lookback_hours`, default 24. Existing obligations are revalidated by exact metadata reads, not discarded when they age outside discovery. Turn reads omit conversation items. Missing completion time on a quota-failed turn is a protocol error, not permission to guess recency.

The `status` command reports only counts by observed source label. It does not print thread previews or conversation bodies.

## Durable obligation state

One obligation is permitted per thread. Each contains:

- exact `thread_id`
- exact `failed_turn_id`
- detection timestamp
- advisory reset timestamp, if exposed
- deterministic `client_user_message_id`
- phase and phase-change timestamp
- exact queued submission ID once known

The phases are:

```text
pending -> dispatching -> submitted
                 \-> uncertain
```

`dispatching` is persisted **before** the queue RPC. If the process loses transport around the send, the state becomes `uncertain`. On restart, the supervisor looks for either an advanced turn or its exact deterministic client message ID in Codex's queue. If neither can be established after the recovery interval, it stops with a diagnostic. There is no unverified automatic retry because that could duplicate work.

## Stale cancellation

A stale obligation is not merely forgotten. If it could have produced a queued submission (`dispatching`, `uncertain`, or `submitted`), the supervisor enumerates the exact thread queue, selects entries carrying its own deterministic client message ID, and deletes those exact queue IDs with `thread/queue/delete`. Unrelated user or client queue entries are left untouched.

There remains an unavoidable narrow concurrency window between the final revalidation and Codex accepting a queue operation because the 0.160.0 queue API does not expose a compare-and-swap precondition against a turn revision. The implementation minimizes this window and cleans stale queued work as soon as it is observable; it does not claim atomicity the API does not provide.

## Rate-limit policy

`ordinaryUsageAllowed` is the authority for recovery. A reset timestamp or `usedPercent` is never treated as proof that usage is available. Exhausted-window reset times are retained only as an advisory wake/sleep hint and for diagnostics.

Multiple obligations are dispatched oldest-first. After each successful submission, the supervisor re-reads account rate-limit permission before considering another thread.

## Approvals and user input

The app-server can send requests from server to client for approvals and explicit user input. This supervisor deliberately never responds to them. It closes the app-server connection after each cycle, and specifically after any `thread/resume`, so it cannot remain a long-lived competing subscriber.

## Single instance and startup

`run` and `once` acquire the per-user OS file lock before loading state. A second supervisor fails immediately. State writes flush and sync the temporary file before atomic replacement. Loaded state must carry the deterministic client message ID for its exact thread/turn identity before it can claim or delete queue entries.

`install-startup` creates a description-owned native `.lnk` shortcut in the user's Startup folder using Windows Shell through bounded PowerShell 7. It directly targets `pythonw.exe`, pins an absolute config path, and invokes no batch shell. Standard Windows `pythonw.exe` is required. Installation and removal refuse unmanaged or link/reparse targets.

`start` launches one hidden supervisor and verifies that it acquired its lock. `stop` writes a per-user stop request and waits up to 60 seconds for lock release. The supervisor finishes its current cycle, closes its connection and stops. Sleep and reconnect waits check the request every second. Pending obligations remain durable. A fresh run clears an old stop request only after acquiring the lock.

`status` probes the instance lock to report whether a supervisor is running. The main log rotates at 2 MiB with 2 backups. RPC diagnostics report the method and numeric error code, without server-provided error bodies. Each RPC has a total deadline that notifications, pings and fragmented frames cannot extend.
