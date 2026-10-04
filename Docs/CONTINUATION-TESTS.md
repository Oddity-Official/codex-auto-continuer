# Native continuation tests

Test quota recovery without exhausting an account. The suite runs the installed, unmodified native Codex executable against a local service. It exercises CAC's real recovery engine, socket transport, durable state and telemetry. It does not use a fake `AppServerClient` or manufacture RPC results.

## Run the suite

Install the development dependencies as described in [Contributing](../CONTRIBUTING.md), then run from the repository root:

```powershell
pwsh -NoProfile -File scripts/verify-continuation.ps1
```

Optional `-PythonPath` and `-CodexPath` select explicit native executables. Codex 0.160.0 is the verified baseline. Missing or incompatible Codex fails the check rather than skipping tests. Keep the checkout path short enough for the 107-byte native socket limit; the gate explains this restriction if needed.

This is a separate integration gate. The regular Windows/CI gate does not need Codex, a login or an account. The integration suite adds no dependencies beyond `.[dev]`. Current results belong to [VALIDATION.md](VALIDATION.md#native-continuation-chain).

## What is real

The successful chain is:

```text
local HTTP 429 usage_limit_reached
  -> native Codex failed turn, persisted usageLimitExceeded + completedAt
  -> CAC records the exact thread/turn obligation on disk
  -> native account/rateLimits/read validates synthetic account and user identity
  -> CAC waits while ordinaryUsageAllowed is false
  -> local usage service allows ordinary usage
  -> CAC revalidates and submits saved Continue through native thread/queue/add
  -> original native writer consumes the shared queue
  -> local response stream completes the same chat's next turn
  -> CAC records observed completion and does not send again
```

Two independent Codex app-server processes share one disposable home. The observer sees the owner's chat as `notLoaded`. CAC handles the exact native active-writer error and queues without taking ownership. Native `thread/start` produces interactive `vscode` source metadata. This is an app-server integration test, not a launched VS Code extension or Desktop UI.

The harness selects the isolated socket directly and probes capabilities. It does not call production daemon discovery or register a CAC process in the user's control directory. Recovery decisions, RPCs, queue writes, persistence and logging use unchanged application code. Restart checks create a new engine and connection from saved state; they are not an operating-system restart or a tray lifecycle test.

## What is simulated

Only the service boundary and explicit transport faults are simulated:

- the loopback inference endpoint returns a structured quota error or a valid successful response stream
- the loopback usage endpoint returns account permission and identity; native Codex derives `ordinaryUsageAllowed`
- one fault discards a real successful queue response after native acceptance
- another closes transport before the queue write, leaving an intentionally uncertain intent

The quota response retains 100% usage and an already-past reset throughout recovery. These misleading hints cannot authorize a send. The tests require the validated permission field instead.

Backend shapes follow first-party source at the matching release: [account quota fixtures](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/tests/suite/v2/rate_limits.rs), [synthetic authentication fixtures](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/tests/common/auth_fixtures.rs), [identity validation](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/src/request_processors/account_processor.rs), and [response stream fixtures](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/tests/common/responses.rs). A custom model provider alone cannot mock account usage. The suite also redirects `chatgpt_base_url` and supplies synthetic file-backed authentication.

## Scenarios and assertions

| Scenario | Required outcome |
| --- | --- |
| Recovery, unrelated chat and restart | Three denied scans send nothing. Reload preserves the obligation. Verified recovery sends exactly one saved `Continue`; the same chat completes. Another successful chat remains untouched. Reload and three further scans produce no additional turn or queued item. |
| Wrong account identity | Native Codex returns null permission despite backend allowance. CAC preserves the obligation and sends nothing. |
| Wrong user identity | The same fail-closed behavior applies to a different user on the reported account. |
| Manual progress before recovery | A new native user turn cancels stale work while usage is still denied. Later permission and reload do not add a continuation. |
| Invalid then edited prompt | An empty saved file raises a helpful error before queue submission, preserving pending state. Repair sends the newly saved text, not a cached/default prompt. |
| Two failed chats | Permission is rechecked after the first send. Denial stops fan-out; only later verified permission continues the remaining chat. Each chat gets exactly one continuation. |
| Accepted send, lost response | Native queue accepts and completes the turn, while CAC saves uncertain state. Reload reconciles progress without resending. |
| Write not accepted | No native queue entry or advanced turn exists. After the reconciliation deadline CAC fails explicitly, including on another cycle, without resending. |

The successful chain also checks local Private telemetry for detection, false-to-true quota permission, separate ownership, saved intent, one submission and observed completed-turn metadata. Actual chat/turn IDs, synthetic credentials and conversation bodies must be absent from those logs. The existing unit suite covers additional privacy, rotation and detailed-mode behavior.

## Isolation and deadlines

Every case uses a unique ignored `.data/n...` home, synthetic credentials, fresh chats, a temporary CAC data folder and isolated child-process home/control environment. No real authentication file is read or copied. User settings, prompt, pending state and installed monitoring processes are not changed.

Shared settings for every scenario are:

| Setting | Value |
| --- | --- |
| Model and provider | `fixture-model`; loopback Responses API; synthetic fixture key |
| Codex sandbox and approvals | `read-only`; `never`; fixed no-tools instructions |
| Inference retries | Request and stream retries both 0; WebSocket inference disabled |
| CAC scope and lookback | Built-in three interactive clients; 24 hours |
| CAC dispatch spacing | 0 seconds, to make multi-chat permission checks deterministic |
| CAC telemetry | Private; diagnostic trace off; default bounded retention |
| Account fixture | Synthetic matching account/user, Pro plan, 100% used, reset 60 seconds in the past |
| Initial usage and inference | Permission false; structured HTTP 429, except the unrelated successful chat |

Scenarios explicitly change permission, identity, saved prompt or transport behavior as shown in the matrix. Successful fixture responses contain only an assistant message, with no tool call.

Both account and model endpoints use `127.0.0.1`. Apps, plugins, remote model discovery, analytics and telemetry exporters are disabled in the disposable Codex configuration. Child HTTP/HTTPS proxies reject external destinations rather than forwarding them; unexpected fixture traffic fails the test. This is configuration-level isolation, not an operating-system network sandbox.

The complete gate has a 240-second process-tree deadline. Server readiness allows 15 seconds, readiness RPCs 3 seconds, normal RPCs 5 seconds, each turn 20 seconds, and cleanup commands 5 seconds. The local HTTP server uses five-second connection timeouts. Cleanup closes CAC connections, terminates only the spawned process trees and removes the disposable home, including synthetic chats and logs. Raw service requests, credentials and conversation bodies are never saved as public evidence.

## What this cannot prove

A passing suite proves the tested native recovery path under controlled service responses. It does not establish real OpenAI account-reset timing, live service availability, every Codex version, actual extension/Desktop UI behavior, or atomic queue idempotency. A natural quota-reset observation remains useful confirmation, but is not needed to exercise the recovery chain repeatedly and safely.
