# Native queue control and history investigation

Date: 4 October 2026, America/Los_Angeles. Starting CAC source: `afd6992b321700e4ecec69b6bfc52453afb1e338`; installed CAC remains 0.5.2. Native Windows 11 x86_64, PowerShell 7, project CPython 3.13.7 and unmodified official Codex 0.160.0. Executable SHA-256: `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`.

## Outcome

History can resolve whether a specific queued input was consumed. The full-history user item's `clientId` preserves the queued submission's `clientUserMessageId`, including when read through another server owner. This establishes entry into the conversation, not successful completion or absence of side effects.

Native owner interruption and selected queue start work. A separate owner cannot perform those operations on the loaded source thread. In-place rollback/message-removal methods are unavailable in this build. A before-turn fork provides the desired shortened context in a new thread, not the original chat.

CAC's saved continuation stays exactly the user's prompt, initially `Continue`. No recovery wrapper, production queue hold, message removal, replay, cancellation or automatic fork was implemented.

## Test matrix

| Scenario | Settings and action | Measured result |
| --- | --- | --- |
| Consumption and duplicate text | One quota-failed turn plus a queued turn with identical text; hold the second inference response; read full turns through both owners | Both owners show two verbatim matches with distinct item IDs, but exactly one matching client ID. Deleting the consumed queue entry returns false. Separate-owner interruption returns -32600 and leaves the turn active |
| Owner interruption | Cancel the held active turn from a second connection to the same owner; retain one pending follow-up; wait 11 seconds | Interrupted turn, zero new inference calls, one queued item retained, consumed input still present in history |
| In-place history removal | After interruption, call thread/rollback, turn/delete and item/delete on the actual owner | All rejected with -32600; full source history unchanged. The generated request schema does not include these methods |
| Selected continuation | Preserve an earlier waiting input; append literal Continue; attempt selected start through peer, then owner with usage permission true | Peer rejected with -32600. Owner starts Continue first, then automatic processing completes the waiting input. Four total turns and empty queue; prompt remains literal Continue |
| Lost deletion response | Pause the owner first; save a pending input; accept deletion but drop the native acknowledgement; reconnect and inspect queue/history | Entry absent from queue and history, no inference for it; saved input successfully restored to the paused queue. This shows useful reconciliation under a verified hold, not a general mutation retry guarantee |
| Before-turn recovery fork | Pause source owner; fork through the peer with beforeTurnId excluding consumed input; run Continue, then two synthetic follow-ups sequentially | New thread initially excludes consumed input; four final fork turns. Source history unchanged and its pending queue still held |
| Serialized outbox | Pause owner, capture and remove two unconsumed inputs, complete selected Continue with native queue empty, deny usage again, then restore permission before each individual replay | Saved inputs remain held during denied permission; literal Continue precedes both inputs in their original order. Five source-thread turns; foreign-owner replay completion waits measured 8.24 and 9.99 seconds |

Final run: 7 passed in 44.39 seconds. The initial six-case round passed in 21.36 seconds. `RESULTS.json` contains sanitized field/count/outcome evidence, without real thread IDs or conversation content. Probe assertions check actual native outcomes, not fabricated app-server responses.

## Reproduction

Install the declared development dependencies in the project virtual environment. Supply an actual native executable, not a shell launcher:

```powershell
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-02/probe_queue_control.py', '--codex', 'C:\Path\To\codex.exe') -TimeoutSeconds 150
```

Every case uses the existing NativeFixture with two isolated app-server processes sharing a disposable home. Authentication is synthetic, account/model services are loopback-only, inherited credentials/endpoints are stripped, and unexpected service traffic fails the fixture. Approvals are never and sandbox is read-only; generated replies do not call tools. The usage endpoint initially denies permission and model inference returns structured HTTP 429 quota failure. A bounded gate then holds one inference response to expose a deterministic active turn for cancellation/race checks.

Each RPC deadline is 12 seconds, native startup is bounded at 15 seconds and the HTTP gate is 15 seconds. Control waits are 10 seconds; foreign-owner replay completion waits are 20 seconds to include discovery, execution and persistence beyond the ten-second watcher interval. The outer command deadline terminates subprocess children. The owner-interruption case crosses that watcher interval. Fixtures close clients, release HTTP gates and terminate both native process trees.

Initial development runs exposed expected Windows ConnectionAbortedError after cancellation of the synthetic stream; the probe now handles only the three expected connection-close exceptions. An intermediate result compared the user item's separate id rather than clientId. The final probe compares the correct field and asserts one match on both readers. Those intermediate diagnostics are not the final identity result.

The first serialized-outbox attempt failed its ten-second completion wait. A foreign-owner queue write is discovered by a ten-second poller and still needs turn execution/persistence, so that wait incorrectly consumed the entire budget on discovery. It was changed to the existing fixture's twenty-second completion budget with phase diagnostics. The final run retained every queue/order/quota assertion; it did not retry production sends or remove safety checks.

## Interpretation and limits

Verbatim text is useful when a new message is unambiguous, but duplicate text and interleaved manual messages make it weaker than client identity. Queue consumption is not successful execution. Cancelling a turn prevents further work but cannot undo prior commands, file writes or external requests. Removing a history entry would not undo those actions either.

The [official app-server documentation](https://learn.chatgpt.com/docs/app-server) describes turn interruption and a deprecated rollback endpoint. This installed build accepts interruption but rejects rollback, so documentation alone is not an availability guarantee. Installed schema inspection and native calls establish the version-specific result.

The matching upstream queue service skips automatic dispatch on interruption. An actual owner can use thread/queue/start with a selected queuedSubmissionId; this avoids the add-then-reorder race when the owner is already held. Shared queue storage does not give the separate CAC server ownership of that turn. No supported production connection to every Desktop/extension/CLI owner was established here.

Forking changes thread identity and leaves the original source untouched. Both chats share workspace state; a fork does not restore the filesystem. Approval routing, original client display, goals, concurrent edits, attachments and partial tool side effects need separate evidence before any production fork/hold feature. This probe does not claim a production-ready mode or quota bypass.

Interruption is not a persistent hold across a subsequent completed turn: completion resumes automatic queue processing. To check usage before every later input, the serialized-outbox probe removes all remaining native entries first and releases only one at a time. It retains saved inputs in a synthetic in-memory list, not a durable private journal. Production crash recovery, encryption and user-intervention policy were not implemented or certified. The already consumed, interrupted input remains in same-thread history.

The running App, settings, prompt and state were not test targets. They still match the saved deployment baseline; App reports 0.5.2, monitoring, zero pending and no error. No real account allowance or user chat was consumed. Application runtime and binary artifacts are unchanged.
