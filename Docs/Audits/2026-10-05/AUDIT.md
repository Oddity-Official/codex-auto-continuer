# Real client connection and composer investigation

Audit date: 2026-10-05
Started at: 2026-10-05T08:19:22.591417+00:00

## Conclusion

CAC 0.6.1 repairs the loaded quota recovery defect described below. Automatic recovery passed through both the unmodified native server and actual CLI composer. Queue holding remains partial: CLI input is client-local, and isolated Desktop/VS Code composer tests reached a Windows setup barrier. A temporary chat in the configured Desktop profile accepted actual follow-ups, but timed polling did not certify interception.

Installed Desktop and the current installed VS Code extension can initialize against a real managed owner that CAC observes. These are isolated connection proofs, not shipped client integrations. Source repairs and follow-up results are separated from the baseline observations below.

Normal CLI Tab-queued input stays in the TUI's local queue. CAC observed the actual owner but had no server queue item to capture. The TUI submitted that input after a synthetic quota failure while ordinary usage was still denied. Connecting to the owner alone does not solve CLI composer holding.

The baseline CLI experiment reproduced a recovery defect: the native loaded chat reported `systemError` with a completed `usageLimitExceeded` turn. CAC recorded the obligation but deferred Continue after a fresh true permission read. An explicit native-queue diagnostic then accepted and completed Continue. That diagnostic was not a CAC recovery pass; the production repair and new automatic pass are recorded in the follow-up section.

## Baseline settings and mutation boundary

| Item | Setting |
| --- | --- |
| Platform | Native Windows 11 x86_64, PowerShell 7, CPython 3.13.7 |
| CAC source | 0.6.0; application source unchanged from `5b58344` |
| Packaged CLI and managed server | Codex 0.160.0 |
| Desktop | Installed package 26.930.4958.0; initialize reports 26.930.41038 |
| VS Code extension | Reinstalled official `openai.chatgpt` 26.930.51102; bundled Codex 0.160.0 |
| Account and service | Disposable synthetic file-backed authentication and rejecting loopback HTTP service |
| Inference | Synthetic structured quota errors and fixed SSE responses; zero real model/account requests |
| Supervisor | Actual `Supervisor.connect()`, explicit packaged executable and isolated process environment; no connection-method replacement |
| Capture | `queue_holding = true`, default all-client selection, existing DPAPI holder |
| CLI input | Real ConPTY terminal; initial argv prompt, typed follow-up and actual Tab queue gesture |
| Desktop transport | Installed endpoint override; transparent loopback TCP-to-native-Unix WebSocket relay |
| Extension transport | Original installed bundle in an isolated extension-development host; executable setting selects disposable compiled stdio/WebSocket adapter |
| Privacy | Private fixture telemetry; relay summarizes only methods/public initialization identity |
| Bounds | CLI wrapper 120 seconds; GUI wrappers 140 seconds; GUI observation 35 seconds; bridge lifetime 60 seconds; RPC/cleanup deadlines enforced |

All homes, profiles, fixture daemons and bridge binaries belong to the disposable experiments. Normal Desktop/Code processes, real chats, deployed CAC, login startup, saved prompt and user settings are outside the mutation boundary. The proxy rejects rather than forwards external traffic. This is application configuration isolation, not an OS firewall claim. Compiler output lives in the ignored fixture home, never public audit evidence.

## Baseline results

| Experiment | Observation | Meaning and limits |
| --- | --- | --- |
| Installed Desktop connection | Actual initialize, account/configuration/project reads, no relay errors, zero inference requests | Endpoint override reaches the native owner CAC observes; composer, holding, replay and production relay security remain untested |
| Current extension connection | Actual VS Code initialize, configuration/chat-list reads, no relay errors, original file hashes unchanged | Executable adapter can connect the real bundle; development-setting support, launch-setting parity and composer holding remain unverified |
| Normal CLI composer | Ready same-owner CAC watcher, visible terminal input, zero native queued items, zero captures | TUI composer queue and app-server queue are different surfaces |
| CLI quota sequence | Queued input reached service while usage stayed denied; native latest error `usageLimitExceeded`; one CAC obligation | Queued-input failure is reproducible without a real account limit |
| CAC recovery | Zero Continue submissions; telemetry reason `runtime_system_error` | Existing guard blocks this actual-client loaded quota state; automatic recovery acceptance failed |
| Explicit native diagnostic | One literal Continue accepted and completed after permission returned | The server can recover this measured state; this deliberate policy bypass is not a CAC recovery pass |

The shared-owner CLI thread reported `source=vscode`, `originator=codex_auto_continuer`, despite real TUI input. CAC initialized before the TUI. This is an observed filtering caveat, not a proven global originator cause. The probe uses default all-client selection and does not certify CLI-only filtering on this path.

## Installed code and upstream evidence

Desktop reads `CODEX_APP_SERVER_WS_URL`. Its local-daemon branch explicitly excludes Windows. Setting `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` alone is not a Windows integration. `CODEX_ELECTRON_USER_DATA_PATH` permits an isolated profile and separate single-instance lock. These are observed implementation hooks, not a documented long-term support promise.

The current extension still spawns a stdio app-server. [Official IDE settings](https://learn.chatgpt.com/docs/developer-settings?surface=ide) describe its alternate-executable option as development-only and warn that it can break behavior. The test adapter forwards original JSON lines as WebSocket messages and native responses to stdout. It does not synthesize replies or apply launch configuration overrides to the already-running server. Launch-setting parity remains unverified.

Both installed GUI bundles contain a queued-follow-up path calling `thread/queue/add` or `thread/queue/update`. Desktop's path is in `webview/assets/app-shared-e20a5fe9db04.js`; the inspected extension path is in `webview/assets/app-initial-2f14c3dc3dba.js`. This is static evidence, not clicked-composer acceptance.

The [0.160.0 TUI input flow](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/tui/src/chatwidget/input_flow.rs) puts queued composer inputs in local `queued_user_messages`. The [composer](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/tui/src/bottom_pane/chat_composer.rs) defines Tab as queue. The ConPTY probe confirms this distinction. CLI `--no-daemon` and many `-c` overrides select embedded mode; the probe uses neither.

[Official app-server documentation](https://learn.chatgpt.com/docs/app-server) describes the transports and marks WebSocket support experimental. A loopback endpoint is not automatically production-safe. Local-user access, authentication, lifecycle, client settings, updates and approval routing still require design and tests.

## Reproduction

Run from the checkout with its development environment. Supply installed client paths. Never replace real profiles or authentication. Scripts stop exact fixture process trees and attempt profile cleanup. Native sandbox setup can leave protected files, as recorded below. Installed sources are never patched.

```powershell
& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_cli_composer.py') -TimeoutSeconds 120

& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_desktop_connection.py', '--desktop', $DesktopExe) `
  -TimeoutSeconds 140

& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_vscode_connection.py', '--code', $CodeExe, '--extension', $ExtensionDirectory) `
  -TimeoutSeconds 140
```

`inspect_clients.py` reads bounded ASAR members without extraction. `--find` scans only app/conversation/queue bundles. Use `--pattern=--listen` for a literal beginning with a dash. Copied installed bundles do not belong in public evidence. The minimal CLI reproducer and all essential results remain in this report after supporting-file retention expires.

## Failed preliminary checks

These failures are retained, not counted as passes:

- CLI-source-only discovery found no row. All-source discovery exposed actual metadata. CLI-only CAC selection then excluded that row. Default all-client selection and the filtering caveat are explicit
- recovery timed out. Added diagnostics identified local queue draining, exact quota failure and CAC's `runtime_system_error` deferral. The final direct queue diagnostic does not mask the failed automatic recovery
- one assertion looked for telemetry `reason` at the root, not in `fields`; the assertion was corrected without changing runtime behavior
- the extension executable could not bootstrap a complete daemon package. The corrected probe uses the complete installed official CLI package and records both versions
- the first extension predicate expected startup `getAuthStatus`. This bundle instead initialized and read configuration/chat lists. The final criterion uses that observed sequence and does not claim authentication/composer acceptance
- a broad webview search exceeded its 128 MiB bound. Inspection was narrowed to named client bundles instead of removing the bound

## Baseline acceptance gaps

At baseline: P1 for the reproduced loaded-quota recovery deferral; P1 for missing actual composer integration; P2 for shared-owner client-filter provenance. The recovery repair below closes the first defect, not the other acceptance gaps.

Desktop and extension need actual composer tests: active capture, denied usage, unchanged Continue, successful recovery, ordered individual release, normal completion, renewed exhaustion, reconnect/restart, uncertain writes, attachments, edits/deletes, approvals and concurrent chats. A connection pass does not waive those tests.

CLI needs a supported client-queue/input hook or an explicitly designed client integration. A relay does not expose the TUI-local queue. Do not advertise polling as equivalent protection.

Repair the loaded quota `systemError` case narrowly, preserving guards for unrelated failures and uncertainty. Verify shared-owner CLI provenance before claiming independent CLI filtering on this path.

Native Windows GUI input tools were unavailable during the baseline investigation. They became available for the user-authorized follow-up below. The approved UI brief remains in `Docs/PRODUCT.md`; this investigation does not implement it.

## Baseline delivery checks

The final Desktop and extension connection probes completed their declared criteria. The final CLI reproducer confirmed the negative automatic-recovery result and the explicit native diagnostic. Preliminary failures above remain part of the evidence.

Current Python helpers compile; the actual extension probe compiled its C# helper. Documentation validation checked 115 local links with zero failures. Audit and transport regression tests passed 44 scenarios in 31.22 seconds. Git whitespace checks passed. Managed cleanup found zero deletion targets. The installed CAC tray and monitor retained their original PIDs; no disposable native fixture process remained in the final process inspection.

No application source or binary changed. The 0.6.0 Windows/recovery release gates remain prior unchanged-source evidence, not fresh certification for the missing composer integrations. The delivery source handoff excludes deployed binaries, temporary profiles, compiled bridges, synthetic credentials, runtime journals and logs.

## Recovery repair and real composer follow-up

The user authorized actual GUI input and temporary use of the configured normal profile. Computer Use controlled the installed clients directly. CAC's production dispatch never uses GUI automation.

### Repair boundary

The supervisor now permits loaded `systemError` recovery only when the latest completed turn matches the durable quota-failure obligation. It requires a finite completion timestamp, fresh true usage permission and another exact-thread/turn check before sending. Holding is not required. Newer non-quota failures, active work, approvals, missing timestamps, unsupported contracts and uncertain sends retain their existing guards. The obsolete holding-specific permission method was removed.

The actual ConPTY CLI probe now lets production CAC perform the recovery; it no longer injects a diagnostic Continue. One Continue completed after permission returned, and three subsequent scans sent none. The CLI-local queue still drained after denial and was not captured. `pywinpty` is a Windows development dependency only, not a bundled runtime dependency.

### Actual client matrix

| Client and settings | Actual input and observation | Result and limit |
| --- | --- | --- |
| CLI 0.160.0, native ConPTY, default managed owner, All clients, 120-second bound | Initial argv prompt; typed follow-up with Tab; quota denial and later true permission | Automatic CAC recovery passed; one completed Continue, three duplicate-free scans. Native queue before failure: zero; held inputs: zero. CLI-only provenance remains unverified |
| Desktop package 26.930.4958.0, isolated profile/auth, native owner relay, read-only fixture, 480-second observation and 600-second wrapper | Actual onboarding/navigation; composer blocked by Finish Windows setup | No model requests and no holding pass. Desktop started `windowsSandbox/setupStart` during onboarding without an explicit setup-button click; we did not automate the security prompt or fabricate readiness |
| VS Code 1.140.0, original extension 26.930.51102, isolated development host, stdio bridge, default then read-only fixture | Actual Codex webview opened; both attempts blocked by Finish Windows setup | No model requests and no holding pass. Connecting the bridge does not certify native launch-setting parity |
| Configured normal Desktop, one disposable projectless chat, GPT-6 Luna Extra High, no tools/files/browsing | Initial numbered output, repeated output, then two actual composer follow-ups; queue row visibly rendered | Four native completed turns; each follow-up appeared exactly once with two distinct native client IDs; final queue empty. This is real composer/history evidence, not a quota or interception pass |
| Read-only native observer of that synthetic Desktop chat, 180-second observation bounds, 10-second RPC deadline | Timed discovery/polling and later full-history read | No pre-consumption queue IDs were captured. One attempt expired during UI preparation; another used the wrong metadata field. Corrected discovery uses authoritative `name`, not `title`. These timeouts do not prove queue invisibility or interception safety |

The Desktop composer retains a trailing newline. Test-marker identification trims whitespace; production input and delivery identity remain unchanged. History correlation uses the native user item's `clientId`, not prompt equality. Private result files remain in ignored `.data`; no actual thread ID, user chat title, screenshot, credential or raw conversation was added to public evidence.

The synthetic normal-profile chat was archived after all four turns completed. The new-chat model preference was restored to GPT-6.1 Sol Extra High. The original CAC chat view was restored. Existing real chat content and model settings were untouched. No model other than the user-authorized GPT-6 Luna was called by this follow-up.

### Cleanup and repeatability

No probe process remained in the final process inspection. Successful native and VS Code fixtures cleaned up. Two ignored Desktop fixture directories retain protected sandbox files: one earlier interrupted run and one onboarding run. Windows denied their removal; no ACL/security-account repair was attempted. These directories are excluded from Git, source handoffs and release artifacts. The native daemon that outlived failed cleanup was identified by its exact fixture executable path and stopped.

`probe_gui_composer.py` preserves the GUI harness for future acceptance work. It requires actual human or supported Computer Use composer input. Do not run it unattended expecting a holding pass or bypass Windows setup. `probe_live_composer_queue.py` is read-only and identifies only the exact synthetic marker, optionally under its authoritative test title. It never resumes, interrupts, removes, replays or sends an input.

```powershell
& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_gui_composer.py', '--desktop', $DesktopExe) `
  -TimeoutSeconds 600

& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_gui_composer.py', '--code', $CodeExe, '--extension', $ExtensionDirectory) `
  -TimeoutSeconds 600

& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
  -Arguments @('Docs/Audits/2026-10-05/probe_live_composer_queue.py', '--socket', $NativeSocket, '--title', $SyntheticChatTitle) `
  -TimeoutSeconds 210
```

### Remaining acceptance work

No new all-client queue-holding feature is certified. Desktop/VS Code need a production owner transport with preserved client configuration, security and approvals, followed by the full composer matrix above. CLI additionally needs a supported TUI-local input hook. Peer queue polling cannot substitute for either integration. The current release keeps holding off by default and leaves normal quota recovery independent of it. Current gates, release and installation results belong to [verification](../../VALIDATION.md).

### Native lock race found during release verification

The first versioned 0.6.1 native gate failed the successful-turn holding scenario: 17 passed, one failed in 117.62 seconds. Publication stopped. A narrow run passed, but independently restarted diagnostic probes reproduced the failure. One series failed on its first trial; another passed 4 trials then failed on trial 5. Neither series counts as a completed 20-trial pass.

Failure telemetry identified `PermissionError` at the placeholder write in `SingleInstanceLock.acquire`. The observer had stopped, the journal was empty, both inputs remained queued and the native turn was still active. The service's 15-second gate had not expired. This was not a queue timeout, model failure or missing notification.

The owner truncates its PID metadata while holding the Windows byte-range lock. A contender could observe an empty file and write a placeholder before locking. Windows correctly denied the overlapping write. The journal retries only `AlreadyRunningError`, so this unrelated write escaped the contention path and stopped observation.

The lock now acquires ownership before writing any byte, including for an empty file. Native Windows supports the locked range beyond EOF. A deterministic regression empties the PID metadata under a held lock; it failed with the exact PermissionError before repair and passed afterward. Existing reusable-lock and second-process exclusion checks still pass. This changes lock ordering, not timeout length or security policy. The focused lock/holding suite passed 12 tests in 0.86 seconds. Final repeated native and full gate results are recorded in verification.
