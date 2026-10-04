# Recovery availability and queued-input investigation

Date: 4 October 2026, America/Los_Angeles. Starting source: `e54235e`; installed release: CAC 0.5.1. Environment: native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Private runtime/session evidence was inspected locally; identities, titles, message bodies and local paths are not exported in this report.

## Confirmed failure

At 07:40:48 and 07:40:50, successive queued follow-ups became turns and failed with structured `usage_limit_exceeded`. CAC detected the latest failed turn and retained one exact-thread obligation through subsequent denied-permission scans.

At 08:00:13, `account/rateLimits/read` returned JSON-RPC internal error `-32603`. CAC's background supervisor handled transport errors but allowed this read-only server error to escape. It exited before the reported approximately 08:02 quota reset. State still contained the obligation. The fatal snapshot replaced the last scan, compatibility and pending count with generic repair advice, making the UI misleading.

A later bounded `status --live` succeeded and reported ordinary usage allowed. Restarting the installed supervisor restored monitoring. The newer manual turn made the saved obligation stale; CAC cancelled it without dispatching an old continuation. No user queue entry was removed. This establishes the immediate availability failure, not the exact upstream cause of that one server error.

The inspected upstream account processor maps usage-service fetch failures and missing snapshots to internal errors. Authentication-required failures use a different invalid-request path. A read-only internal error can therefore be retried while withholding all dispatch authority; an arbitrary RPC error cannot.

## Repair

CAC 0.5.2 reconnects after internal quota-read errors with bounded backoff, clears current permission and preserves pending state. Other request/contract/mutation errors remain diagnostic failures. Status retains actual pending count, prior scan and compatibility, and shows safe method/code and actionable guidance without server error bodies.

## Native reproduction

The permanent native regression queues two synthetic follow-ups on an unmodified Codex 0.160.0 owner while inference returns local quota failures. All three turns fail with structured quota errors. CAC records the latest failure. The loopback usage service then returns HTTP 503, producing native `account/rateLimits/read / -32603`. CAC closes the connection and preserves state bytes with no inference. The service recovers while permission remains false; CAC resumes scanning but still does not send. After explicit true permission, exactly one saved Continue completes the original chat, with no later duplicates.

Focused native check: one passed in 11.10 seconds, command deadline 120 seconds. Standard native settings remain 12-second RPC deadlines, 20-second turn waits and isolated fixture homes/authentication. A first test attempt exposed that the direct-server fixture pinned only its initial connection; the fixture now pins every reconnect to the synthetic socket. That failed attempt performed read-only user-daemon discovery and a rejected read of a synthetic thread ID, not user mutation. The corrected reproduction uses only fixture sockets.

## Queue-order boundary

The inspected schema also has update, reorder and explicit start endpoints, in addition to CAC's consumed add/list/delete subset. Reorder accepts queue submission IDs; it is not a hold switch or an atomic add-at-front operation. The verified add parameters contain only thread ID, input and client message ID. No verified pause, prepend transaction or client-composer queue ownership contract is available. Reading/storing message bodies would not create these guarantees. No interception, user-message removal/replay or conversation storage was implemented.

Matching upstream [queue processor](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs) and [queue service](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/ext/queue/src/service.rs) show enqueue followed by `wake_if_loaded`; reorder is a separate call with its own dispatch lock. Reordering after enqueue cannot guarantee that the owner has not already begun consumption. The native queued-failure test confirms automatic consumption while quota is denied.

The immediate stranded-chat defect is repaired without those mechanisms. Client-local queue sequencing remains an upstream integration question, distinct from CAC's durable quota recovery. Latest-message text equality is not delivery identity: manual messages and earlier identical prompts can match. Existing exact message-ID and newer-progress reconciliation remains the authority.

## Evidence helper

`probe_session_events.py` extracts a finite lifecycle slice and emits timestamps, event types, message lengths, Continue classification and structured quota classification, never message text or thread IDs. Supply a private session path plus `--after` and `--before`. Run through `scripts/run-project-command.ps1` with a 25-second deadline. It handles an actively appended final partial line without exporting the log.
