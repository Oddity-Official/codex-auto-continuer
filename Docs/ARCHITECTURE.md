# Architecture

## Runtime

The product runtime is Python 3.13 with no third-party runtime dependencies. `pytest` is development-only. The supervisor is a per-user process intended to run on native Windows 11.

## Control path

1. Resolve `codex` from `PATH` and require CLI version 0.160.0 or newer.
2. Probe the first-party local app-server daemon with `codex app-server daemon version`; optionally start it with `codex app-server daemon start`.
3. Connect to the returned private AF_UNIX control socket and perform the WebSocket `initialize` / `initialized` handshake used by Codex's own daemon client.
4. Poll `account/rateLimits/read` and `thread/list` through JSON-RPC.
5. For recent in-scope threads, read only the newest turn. A continuation obligation is created only for a terminal failed turn whose structured `codexErrorInfo` is `usageLimitExceeded`.
6. Persist that obligation before attempting any continuation.
7. Dispatch only when `ordinaryUsageAllowed` is explicitly `true`.
8. Immediately re-read the exact thread and turn. Any user/manual progress cancels the stale obligation.
9. If an unloaded thread must be joined, use `thread/resume` on the same shared app-server and verify the returned thread ID. The app-server connection is closed after the cycle so this supervisor cannot remain a sleeping approval/input subscriber.
10. Submit the configured continuation through `thread/queue/add` using a deterministic `clientUserMessageId` derived from the exact thread/failed-turn pair.
11. On subsequent cycles, reconcile the durable obligation against the latest turn and `thread/queue/list` before doing anything else.

No UI automation path exists.

## Thread scope

The default `thread_scope = "desktop"` accepts only the configured custom session sources, initially `chatgpt` and `atlas`. This matches the source classifications Codex uses for its interactive ChatGPT/Atlas clients. `thread_scope = "allInteractive"` additionally accepts CLI and VS Code interactive threads; it does not admit `exec`, `appServer`, sub-agent, or unknown sources.

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

`run` and `once` take a per-user OS file lock. A second supervisor process fails immediately with the lock path instead of racing the same obligation.

`install-startup` writes one marker-owned `.cmd` file into the current user's Windows Startup folder and launches `pythonw.exe` when available. Installation and removal refuse to overwrite or delete an unmanaged file at that path.
