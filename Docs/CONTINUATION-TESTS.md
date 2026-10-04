# Native continuation tests

Test quota recovery without exhausting an account. The suite runs the installed, unmodified native Codex executable against a local service. It exercises CAC's real recovery engine, socket transport, durable state and telemetry. It does not use a fake `AppServerClient` or manufacture RPC results.

## Run the suite

Install the development dependencies as described in [Contributing](../CONTRIBUTING.md), then run from the repository root:

```powershell
pwsh -NoProfile -File scripts/verify-continuation.ps1
```

Optional `-PythonPath` and `-CodexPath` select explicit native executables. Codex 0.160.0 is the verified baseline. Missing or incompatible Codex fails the check rather than skipping tests. Keep the checkout path short enough for the 107-byte native socket limit; the gate explains this restriction if needed.

This is a separate integration gate. The regular Windows/CI gate does not need Codex, a login or an account. The integration suite adds no dependencies beyond `.[dev]`. Current results belong to [VALIDATION.md](VALIDATION.md#compatibility-certification).

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

The eight recovery scenarios select isolated sockets directly and grant test-only dispatch access. This lets the suite establish behavioral evidence for candidate binaries before production certification. Recovery decisions, RPCs, queue writes, persistence and logging use application code. Engine reload is not an operating-system restart or a tray lifecycle test.

Three compatibility cases extend the gate to 11 scenarios. One generates the native binary's contract and checks connected identity. Two managed-daemon cases use production discovery and restart/reconnect. Both remove certification to prove Strict preserves pending-state bytes; one then switches to Balanced and recovers the untested stable tuple. They verify one Continue/completed turn and no duplicates. Optional `--daemon-executable` selects another complete package for mixed-version testing. No CAC process is registered in the user's control directory.

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
| Queued failures and usage-service outage | Two queued follow-ups fail with quota errors. CAC retains the latest obligation. Native quota read returns internal error after local HTTP 503; the loop reconnects without changing state or sending. Service recovery with denied permission still sends nothing. True permission then produces exactly one Continue and no duplicates. |
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

The local gate has a 240-second process-tree deadline; hosted CI allows 300 seconds. Server readiness allows 15 seconds, readiness RPCs 3 seconds, normal RPCs the production default of 12 seconds, each turn 20 seconds, and embedded process cleanup 5 seconds. Fresh managed-package bootstrap allows 60 seconds, restart 25 seconds, stop 15 seconds, and schema generation 20 seconds. Cold package setup is not an RPC latency benchmark. There are no automatic test retries. The disposable daemon has remote control and automatic updates disabled, with zero-second shutdown grace. Native Codex creates private socket/state directories; Python must not pre-create them with inherited Windows permissions. The local HTTP server uses five-second connection timeouts. Cleanup closes CAC connections, stops only fixture processes and removes the disposable home. Raw service requests, credentials and conversation bodies are never saved as public evidence.

## What this cannot prove

A passing suite proves the tested native recovery path under controlled service responses. It does not establish real OpenAI account-reset timing, live service availability, every Codex version, actual extension/Desktop UI behavior, or atomic queue idempotency. A natural quota-reset observation remains useful confirmation, but is not needed to exercise the recovery chain repeatedly and safely.

## Installed VS Code extension

Run the separate gate with absolute paths to your installed `Code.exe` and official `openai.chatgpt` extension directory:

```powershell
pwsh -NoProfile -File scripts/verify-vscode.ps1 -CodePath 'C:/path/to/Code.exe' -ExtensionPath 'C:/path/to/openai.chatgpt-version-win32-x64'
```

Optional `-PythonPath` selects the development interpreter. Both paths are required; missing software fails instead of silently skipping. This gate is not part of ordinary CI or `verify-continuation.ps1`. It uses [VS Code's official extension test host](https://code.visualstudio.com/api/working-with-extensions/testing-extension), with a fresh profile and extension directory.

The disposable development manifest retains the installed manifest's version and contributions but selects a test bootstrap. The bootstrap installs read-only transport taps before activation, then loads the original installed JavaScript bundle. Its extension context points to the installed assets and bundled native executable. Before-and-after SHA-256 checks verify that the installed manifest, bundle and executable are unchanged.

The original extension initializes its own app-server transport. The test sends initial thread/turn RPCs through that transport using a disjoint request-ID range. It does not fabricate initialization, metadata, queue responses or completion notifications. CAC connects through a separate isolated native socket and uses its unchanged recovery engine. The extension's original writer consumes the real shared queue and emits the recovered turn's completion notification.

| Check | Required outcome |
| --- | --- |
| Original process and initialization | Bundled EXE, `codex_vscode` originator override, `VS Code` client name and `Codex Extension` title |
| Native provenance | Persisted `source=vscode`, `originator=codex_vscode`; observer sees `notLoaded` |
| Eight client-selection combinations | Accept if and only if VS Code is selected; CLI/Desktop alone and no clients discover nothing |
| Quota denial and saved obligation | Three denied scans cause one durable exact-thread/failed-turn obligation and no send |
| Recovery and original ownership | One saved Continue completes the same thread through the original extension process |
| Duplicate prevention | Three subsequent cycles leave exactly two turns, two inference requests and no queued item |
| Private telemetry | Detection, separate-owner queue submission and observed completion; no bodies, real fixture IDs or credentials |
| Isolation and integrity | Original extension files unchanged; fixture profile, chats and owned processes cleaned up |

This uses the native fixture settings above, except CAC selects only VS Code for recovery. VS Code telemetry and updates are disabled in the disposable profile. Its workbench and extension can still attempt remote feature/configuration requests: the loopback proxy rejects them without forwarding. Rejections are counted rather than treated as unexpected native API routes. Unrecognized local account/model routes or invalid fixture authentication still fail the test. This remains configuration-level isolation, not an OS network sandbox.

The whole gate has a 180-second process-tree deadline. Fixture setup and RPC bounds remain unchanged. The extension driver allows 30 seconds for startup, 10 seconds per native RPC, 90 seconds for recovery and 30 seconds for final observer assertions. Python allows 45 seconds per driver result and 20 seconds for graceful VS Code exit; cleanup uses five-second process-tree commands. The regular installed editor profile, real authentication, user chats and deployed CAC processes are not used.

This gate verifies the installed extension's native owner and client filtering, not typing in the composer or visual webview rendering. It does not prove WSL/remote coverage, actual service-reset timing, production daemon discovery or a fresh Windows login.
