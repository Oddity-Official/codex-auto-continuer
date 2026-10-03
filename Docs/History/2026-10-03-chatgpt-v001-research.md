# Research and provenance

Evidence status is explicit here so implementation details do not turn assumptions into contracts.

## Verified — user environment

### Codex CLI/Desktop parity on the tested install

- Environment reported during project setup: Windows, `codex-cli 0.160.0`.
- Observed command: `codex queue --thread <thread-uuid> --message "Continue"`.
- Observed result: the queued text appeared in the already-existing Codex Desktop thread and started a turn there, including while the account had no remaining usage.
- Provenance: direct user test supplied in the project-creation conversation on 2026-10-02/03.

This establishes that a first-party CLI submission can target an existing Desktop-originated thread by ID on the tested installation.

## Verified — OpenAI Codex source at 0.160.0

Unless otherwise stated, source claims below were checked against `openai/codex`, release `rust-v0.160.0`, commit `a956835d020762cb2b570053af06f643a11c0ecc`.

### Shared app-server daemon discovery

- `codex app-server daemon version` and `start` return JSON lifecycle output containing the app-server control `socketPath` and version metadata.
- The control path is under Codex home's `app-server-control/app-server-control.sock`.
- Codex's own daemon client connects to that AF_UNIX socket, upgrades it as a WebSocket using `ws://localhost/`, sends `initialize`, then `initialized`.
- Source: `codex-rs/app-server-daemon/src/lib.rs`, `codex-rs/app-server-daemon/src/client.rs`, `codex-rs/app-server-transport/src/transport/mod.rs`.

### Thread discovery and source scope

- `thread/list` supports structured sorting/filtering and returns thread IDs, timestamps, status and session source.
- Codex's interactive source set is CLI, VS Code, `Custom("atlas")`, and `Custom("chatgpt")`.
- API session-source values also include `exec`, `appServer`, sub-agent variants and `unknown`, allowing the supervisor to reject non-interactive work explicitly.
- Source: `codex-rs/app-server/src/filters.rs`, `codex-rs/rollout/src/lib.rs`, generated app-server v2 thread/session-source protocol types.

### Exact failed-turn detection

- Turns have terminal `completed`, `interrupted`, and `failed` statuses.
- Failed turns carry structured error information including `codexErrorInfo`; usage exhaustion is represented as `UsageLimitExceeded` in Rust and serialized through the v2 protocol.
- `thread/turns/list` exists for reading persisted/current turn history without scraping UI text.
- Source: app-server v2 protocol and thread read/list implementation at the pinned commit.

### Usage recovery authority

- `account/rateLimits/read` exposes `ordinaryUsageAllowed`.
- Its protocol documentation states that null means unavailable and clients must not infer recovery from percentages or reset times.
- Source: generated `GetAccountRateLimitsResponse` schema/type and app-server rate-limit tests at the pinned release.

Implementation consequence: reset timestamps are advisory only. This project dispatches only on explicit `ordinaryUsageAllowed == true`.

### Queue semantics and stale deletion

- `thread/queue/add` accepts a thread ID, input, and `clientUserMessageId`, returning a `queuedSubmission`.
- `thread/queue/list` returns queued submissions and pagination.
- `thread/queue/delete` accepts `threadId` plus exact `queuedSubmissionId` and returns `deleted: bool`.
- The queue service can consume an item into a loaded idle thread before successful model completion, so pre-queueing while exhausted is not a durable wait-for-reset mechanism.
- Source: `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`, `codex-rs/app-server/src/request_processors/thread_queue_processor.rs`, `codex-rs/ext/queue/src/service.rs`, CLI queue plumbing.

### Resuming an unloaded thread

- `thread/resume` operates through the shared app-server thread manager. A running thread is rejoined; an unloaded stored thread can be materialized/resumed through the same server.
- A resume connection becomes a thread subscriber. Pending server-to-client requests can be replayed to subscribers.
- Source: `codex-rs/app-server/src/request_processors/thread_processor.rs`, `thread_lifecycle.rs`, `thread_state.rs`, `outgoing_message.rs`.

Implementation consequence: this project uses `thread/resume` only when needed and closes its app-server connection after the cycle. It never answers approval or explicit-user-input requests.

### No verified submission idempotency contract

- `clientUserMessageId` is persisted on queued/user-message data, which makes reconciliation possible.
- The reviewed 0.160.0 sources do **not** establish that retrying `thread/queue/add` with the same client message ID is idempotent.
- Provenance: queue protocol/service and turn-input source review at the pinned commit.

Implementation consequence: an ambiguous post-send crash is reconciled against the queue/latest turn; if neither proves what happened, the supervisor fails rather than automatically retrying.

## Verified — implementation tests in this checkpoint

The Linux regression suite covers exact usage-limit classification, null recovery permission, stale/manual-progress cancellation, exact queued-submission deletion, multiple stalled threads, unloaded-thread resume flow, source scoping, crash ambiguity, transient reads, corrupt durable state, single-instance exclusion, WebSocket framing/fragmentation/handshake handling, JSON-RPC behavior, queue pagination and packaging smoke. Exact results belong in `VALIDATION.md`.

## Inferred / design assumptions

- Polling `thread/list` sorted by `updated_at` is sufficient to discover a newly terminal usage-limit turn because a newly persisted turn should advance the thread's update timestamp. The source shape supports this design, but this exact Desktop timing behavior still needs live native verification.
- Closing our connection after each cycle should remove our subscriber role through normal app-server disconnect cleanup. Source supports connection/subscription teardown, but live Desktop coexistence should still be exercised on Windows.

## Missing / native verification required

1. Run the full gate on native Windows 11 with Python 3.13.
2. Exercise a real Codex Desktop usage-limit failure through reset and confirm one continuation lands in the same thread.
3. Repeat with the Desktop thread unloaded before reset.
4. Repeat with two simultaneously stalled Desktop threads and confirm sequential recovery/recheck behavior.
5. Manually advance a thread while this tool has a queued continuation and confirm the exact queued item is deleted on the live 0.160.0 server.
6. Confirm install/startup behavior with the user's actual Python/Codex installation paths.

No UI-automation fallback is planned for any failed native check. Interface incompatibility should fail diagnostically instead.
