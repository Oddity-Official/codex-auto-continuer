# Real client connection and composer investigation

Audit date: 2026-10-05
Started at: 2026-10-05T08:19:22.591417+00:00

## Conclusion

Installed Desktop and the current installed VS Code extension can initialize against a real managed owner that CAC observes. These are isolated connection proofs, not shipped client integrations or clicked-composer acceptance passes. No installed CAC binary or normal client configuration changed.

Normal CLI Tab-queued input stays in the TUI's local queue. CAC observed the actual owner but had no server queue item to capture. The TUI submitted that input after a synthetic quota failure while ordinary usage was still denied. Connecting to the owner alone does not solve CLI composer holding.

The CLI experiment also reproduced a recovery defect: the native loaded chat reported `systemError` with a completed `usageLimitExceeded` turn. CAC recorded the obligation but deferred Continue after a fresh true permission read. An explicit native-queue diagnostic then accepted and completed Continue on the same chat. This is not a CAC recovery pass. The runtime rule remains unchanged pending a narrowly tested repair.

## Settings and mutation boundary

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

## Results

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

Run from the checkout with its development environment. Supply installed client paths. Never replace real profiles or authentication. The scripts stop exact fixture process trees and clean their temporary profiles. They never patch installed sources.

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

## Remaining acceptance work

Priority: P1 for the reproduced loaded-quota recovery deferral; P1 for missing actual composer integration before claiming queue-holding coverage; P2 for shared-owner client-filter provenance. These are current defects or acceptance gaps, not completed repairs.

Desktop and extension need actual composer tests: active capture, denied usage, unchanged Continue, successful recovery, ordered individual release, normal completion, renewed exhaustion, reconnect/restart, uncertain writes, attachments, edits/deletes, approvals and concurrent chats. A connection pass does not waive those tests.

CLI needs a supported client-queue/input hook or an explicitly designed client integration. A relay does not expose the TUI-local queue. Do not advertise polling as equivalent protection.

Repair the loaded quota `systemError` case narrowly, preserving guards for unrelated failures and uncertainty. Verify shared-owner CLI provenance before claiming independent CLI filtering on this path.

Native Windows GUI input tools are unavailable in this session. No automated clicking, composer typing or screenshots are claimed. User-assisted GUI acceptance is needed unless that tool surface becomes available. The approved UI brief remains in `Docs/PRODUCT.md`; this investigation does not implement it.

## Delivery checks

The final Desktop and extension connection probes completed their declared criteria. The final CLI reproducer confirmed the negative automatic-recovery result and the explicit native diagnostic. Preliminary failures above remain part of the evidence.

Current Python helpers compile; the actual extension probe compiled its C# helper. Documentation validation checked 115 local links with zero failures. Audit and transport regression tests passed 44 scenarios in 31.22 seconds. Git whitespace checks passed. Managed cleanup found zero deletion targets. The installed CAC tray and monitor retained their original PIDs; no disposable native fixture process remained in the final process inspection.

No application source or binary changed. The 0.6.0 Windows/recovery release gates remain prior unchanged-source evidence, not fresh certification for the missing composer integrations. The delivery source handoff excludes deployed binaries, temporary profiles, compiled bridges, synthetic credentials, runtime journals and logs.
