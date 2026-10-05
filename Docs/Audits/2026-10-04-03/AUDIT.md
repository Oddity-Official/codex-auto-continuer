# Native queue interception and durable holding investigation

Date: 4 October 2026, America/Los_Angeles. Starting CAC commit: `a9025dd58f709d963b8731d77faae14a0f7facf7`. CAC runtime and installed release remain 0.5.2. Native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Unmodified official Codex 0.160.0 executable SHA-256: `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`.

## Outcome

Proactive capture works well in the measured active-turn owner-listener fixtures. It does not provide universal native-composer interception. Same-owner access matters more than faster polling. Neither tested approach captured an input queued into an already-idle owner.

Confirmed integration hazard: deletion through a separate owner can return true while the actual owner still consumes the input. Do not use that response as proof that replay is safe. The peer's dispatch mutex does not lock the actual owner. In the 50-trial quota-boundary follow-up, 20 inputs were consumed despite accepted deletions.

Private held-input storage is feasible without storing whole conversations. Fresh Python processes recovered synthetic Windows-account-encrypted records. Deletion and replay acknowledgement faults reconciled by exact client ID without duplicate input. These are prototypes, not a production journal or queue-holding feature.

The approved tray/status brief is consolidated in `Docs/PRODUCT.md`, including the user's later decisions. No UI, saved prompt, production queue, installed binary or recovery behavior changed.

## Timing experiment settings

Every cell uses two native app-server processes sharing a disposable home, loopback account/model services, synthetic authentication, stripped inherited secrets/endpoints, approvals never and a read-only sandbox. Fixed replies do not call tools. Each trial creates a new thread.

The initial inference response is held only to establish setup. The observer is already running before enqueue. The response is then released either 250ms after enqueue begins or concurrently with enqueue. No interception acknowledgement holds the native dispatcher. The idle cell completes the initial turn before enqueue. The quota cell returns a real structured HTTP 429 usage-limit response; ordinary usage remains denied. The peer's polling loop sleeps 10ms between completed reads, not a promised 100 reads per second. Owner events arrive through a second connection resumed on the actual owner.

Observed inputs are persisted with flush and fsync before deletion. The initial matrix uses synthetic unencrypted records; the encrypted follow-up includes actual DPAPI encryption before fsync/deletion. Delayed cells add 25ms after persistence, before deletion. Settle checks queue emptiness and terminal full history, then rereads after 40ms. Every submitted input must either be durably captured without consumption or occur exactly once in history. A missed input is never replayed by the race probe.

RPC deadline: 12 seconds. Native startup: 15 seconds. Initial HTTP setup gate: 15 seconds. Race settle: 5 seconds. Worker readiness: 5 seconds; close/join: 3 seconds. Fixture turn completion: 20 seconds. Outer commands terminate their child trees on timeout. Each worker owns its connection exclusively.

## Initial measured matrix

`RESULTS.json`: 13 scenarios passed in 74.09 seconds, comprising 120 timing trials and an observer-offline reconciliation scenario.

| Input timing | Observer | Delay before deletion | Captured before consumption | Consumed | Accepted deletion but consumed | Median observed latency |
| --- | --- | --- | --- | --- | --- | --- |
| Active, 250ms response headroom | Owner events | 0ms | 10/10 | 0 | 0 | 1.180ms |
| Active, 250ms response headroom | Peer polling | 0ms | 10/10 | 0 | 0 | 11.463ms |
| Response released with enqueue | Owner events | 0ms | 10/10 | 0 | 0 | 1.415ms |
| Response released with enqueue | Peer polling | 0ms | 10/10 | 0 | 0 | 16.743ms |
| Already idle | Owner events | 0ms | 0/10 | 10 | 0 | No observed queue item |
| Already idle | Peer polling | 0ms | 0/10 | 10 | 0 | No observed queue item |
| Quota response released with enqueue | Owner events | 0ms | 10/10 | 0 | 0 | 1.405ms |
| Quota response released with enqueue | Peer polling | 0ms | 0/10 | 10 | 4 | 17.223ms |
| Response released with enqueue | Owner events | 25ms | 10/10 | 0 | 0 | 1.619ms |
| Response released with enqueue | Peer polling | 25ms | 1/10 | 9 | 0 | 23.419ms |
| Active, 250ms response headroom | Owner events | 25ms | 10/10 | 0 | 0 | 1.121ms |
| Active, 250ms response headroom | Peer polling | 25ms | 10/10 | 0 | 0 | 22.138ms |

Latency measures enqueue-call start to the queue-list observation, not total deletion time. Medians include observed entries that were later consumed. Per-trial observation/deletion timings and outcomes are retained in JSON. Offline input was consumed once; reconnect correlated its client ID and deletion returned false. No replay was attempted.

## Targeted follow-ups

`QUOTA-STRESS.json`: 2 scenarios, 100 trials, passed in 42.26 seconds. `BOUNDARY-STRESS.json`: 2 scenarios, 100 trials, passed in 46.52 seconds. Each repeats its named cell 50 times, not retries of a failed assertion.

| Input timing | Observer | Delay | Captured before consumption | Consumed | Accepted deletion but consumed | Median observed latency |
| --- | --- | --- | --- | --- | --- | --- |
| Quota response released with enqueue | Owner events | 0ms | 50/50 | 0 | 0 | 1.425ms |
| Quota response released with enqueue | Peer polling | 0ms | 5/50 | 45 | 20 | 17.602ms |
| Response released with enqueue | Owner events | 25ms | 50/50 | 0 | 0 | 1.470ms |
| Response released with enqueue | Peer polling | 25ms | 2/50 | 48 | 2 | 23.193ms |

The quota follow-up and independent durability command briefly overlapped in separate disposable homes. This is ordinary machine scheduling contention, not a dispatch barrier. Counts describe these local runs, not an upstream or cross-machine probability guarantee.

`ENCRYPTED-STRESS.json`: 2 scenarios, 100 additional trials, passed in 46.41 seconds. Encryption and fsync both precede deletion. Owner events captured 50/50; peer polling captured 3/50 and missed 47. Five inputs were consumed despite accepted peer deletions. Median observation latency was 1.558ms for owner events and 18.754ms for peer polling. Combined measured race count: 420 across the initial matrix and three targeted follow-ups. The encryption result does not imply an implemented crash-safe production journal.

## Durability and transport probes

`DURABILITY.json`: 6 scenarios passed in 10.38 seconds.

| Scenario | Native action and assertion |
| --- | --- |
| Saved before deletion | Encrypt and fsync the canonical queue item; decrypt in a fresh process; find original still queued; remove it while owner is held; release exactly once with the original identity |
| Delete request not sent | Close before transmitting deletion; recover encrypted record; find original still queued; remove it under verified hold; release once |
| Delete accepted, response lost | Forward deletion to the real owner and discard its successful response; reconnect and recover; original absent from queue and history under verified hold; restore input once |
| Replay accepted, response lost | Two literal Continue texts, different identities; recover release-requested record; full history has exactly one matching client ID; do not retry |
| Image attachment | Enqueue a local copy of the public CAC icon; native queue snapshots it to an embedded data URL; delete; encrypt/decrypt in a fresh process; restore exact canonical input; remove before inference |
| Stdio owner | Launch a third native server on stdin/stdout; actual owner gets queue notifications; peer resume fails with exact active-writer error; peer sees no queue-change event but can poll/delete while initial turn is held |

DPAPI records are tied to the current Windows account and round-trip through a separate Python process with the fixture environment. Corrupted ciphertext is rejected. This is not a disk-full, power-loss, mid-write-kill, cross-user migration or complete transactional-journal test. Restoring the image into the native queue is verified; model vision execution is not.

## Minimal reproduction and source explanation

Create an isolated chat and hold its initial inference response. Start a peer poller on a different native server sharing only the home. Release a quota-failure response as the original owner enqueues a uniquely identified follow-up. The peer lists the canonical item, saves/fsyncs it and deletes by queue ID. After completion, read `thread/turns/list` with `itemsView=full`. Compare `userMessage.clientId` with the original `clientUserMessageId`, not the item ID or text. Repeat 50 new trials and count cases where delete returned true but matching history still exists.

The [official 0.160.0 queue service](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/ext/queue/src/service.rs) implements `dispatch_lock` in a process-local map. `dispatch_if_idle` reads the first record, builds input, calls `start_turn_if_idle`, then deletes the record. Another process's mutex cannot stop this sequence. A peer can remove the stored row after the owner selected it without undoing the selected input. No distributed compare-and-swap or pre-dispatch acknowledgement was found in this consumer contract.

The [official server transport selection](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/src/lib.rs) chooses stdin/stdout, a Unix-domain socket, WebSocket or off. A stdio owner does not thereby acquire a second local control socket. The [official app-server documentation](https://learn.chatgpt.com/docs/app-server) describes asynchronous lifecycle notifications; these are not a queue dispatch approval handshake. The installed protocol and native calls establish the specific tested capabilities.

## Reproduction commands

Use the project's Python 3.13 virtual environment and an actual official native executable. These commands create no real login/session or paid model call:

```powershell
$codex = 'C:\Path\To\codex.exe'
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-03/probe_interception.py', '--codex', $codex, '--trials', '10') -TimeoutSeconds 180
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-03/probe_interception.py', '--codex', $codex, '--trials', '50', '--select', 'quota-boundary', '--output', 'QUOTA-STRESS.json') -TimeoutSeconds 150
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-03/probe_interception.py', '--codex', $codex, '--trials', '50', '--select', 'completion-boundary and 25', '--output', 'BOUNDARY-STRESS.json') -TimeoutSeconds 150
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-03/probe_interception.py', '--codex', $codex, '--trials', '50', '--select', 'quota-boundary', '--encrypted', '--output', 'ENCRYPTED-STRESS.json') -TimeoutSeconds 150
./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-04-03/probe_durability.py', '--codex', $codex) -TimeoutSeconds 120
```

Helpers locate the checkout rather than embedding machine paths. Retained results contain synthetic counts/timings, no user titles, thread UUIDs, input bodies or credentials. Bodies and native databases exist only in disposable ignored homes. Fixture teardown closes workers/clients, terminates native trees and removes homes. Useful helpers/results travel with the normal source handoff, not the app ZIP.

## Failed development checks

The first race invocation passed assertions in 74.17 seconds but did not export measured cells: pytest loaded a second module instance, so the command's globals did not contain test results or its requested trial override. That run is excluded from the measured evidence. Trial/settings transfer now uses explicit environment values; module teardown exports collected results; the command checks the current run identity before finalizing JSON.

The initial durability invocation passed 5 scenarios and failed attachment enqueue. The hand-written tiny PNG had a bad IDAT checksum, independently reproduced with Pillow verification. The probe now uses a valid existing public icon and retains all attachment assertions. The final six-case run passed. Only expected broken/reset/aborted connections during fixture teardown are handled; unexpected routes, credentials, protocol results and worker failures still fail.

## Implementation decision and limits

Do not implement universal interception as faster peer polling or assume accepted deletion means safe replay. An opt-in proactive holder needs verified owner access, a durable account/home/thread-bound input journal and identity/lifecycle reconciliation. Preserve original order, check ordinary usage before each release and keep the prompt exactly Continue or the user's saved text. Normal completion must release held follow-ups without inventing a recovery turn.

Owner disconnection, missed/idle inputs, manual progress, stale recovery obligations, stop/exit and native-queue restoration need explicit states. Unconfirmed inputs must remain held without blind replay. User inputs need separate lifetime/management from CAC's disposable recovery obligations. Whole conversation storage is not necessary for the demonstrated held-input path.

A strict all-client guarantee requires supported owner-side pre-dispatch integration or routing input through a CAC-owned outbox before native enqueue. No installed client-composer hook, Windows UI interaction, global notification discovery, arbitrary attachment type, side-effect undo or distributed queue barrier is claimed. The current runtime, release and existing continuation gate are unchanged; their prior results are unchanged-source evidence, not fresh checks of a new feature.

## Delivery checks

The five final native commands passed 25 pytest scenarios in total, including 420 measured timing trials, offline reconciliation and six durability/transport scenarios. Both probe sources compile. The local documentation checker passed 110 links. Git whitespace checks passed. Focused inspection of changed docs/evidence found no configured personal-path or common credential-prefix matches; this is a defined check, not a complete secret-detection guarantee. No native fixture processes remained on the selected executable. Managed audit cleanup reported zero deletion targets. No application source, release artifact or installed runtime was rebuilt or changed.
