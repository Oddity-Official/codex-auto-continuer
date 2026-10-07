# Codex Auto Continuer

A portable Windows tray tool that continues the exact Codex chat stopped by a usage limit. It waits until Codex confirms ordinary usage is available. No window clicking, clipboard changes, keystrokes or screen scraping.

This is an independent tool, not an OpenAI product. It uses experimental local Codex interfaces and stops with a diagnostic if their contract changes. See [verified behavior and limits](Docs/VALIDATION.md).

The redesigned tray/status interface is a source candidate awaiting final interactive Windows checks and a new packaged release. The latest stable download is still the previously verified release.

## Launch and use

1. Extract the [latest stable release](https://github.com/Oddity-Official/codex-auto-continuer/releases/latest) into a writable folder. Keep both EXEs and `_internal` together.
2. Launch `CodexAutoContinuer.exe`. Monitoring starts automatically. Look in Windows' hidden tray icons if needed.
3. Right-click the tray icon. Select `Start With Windows` to enable per-user login launch.
4. Select `Modify Prompt` to open `data/continue-prompt.md` in your default Markdown editor. The default is simply `Continue`. Save as UTF-8; the next continuation reads the saved file.

You need Windows 11 x86_64 and a signed-in native Codex installation. The release bundles Python and tray dependencies; users do not need Python, PowerShell 7, WSL or administrator rights. Startup management can use Windows' built-in PowerShell.

CAC 0.6.1 certifies the official Windows Codex 0.160.0 CLI/daemon build. Default Balanced mode also permits unknown stable builds after identity, schema and runtime checks, with an untested notice. Strict mode requires an exact recovery certificate. Status explains the evidence; real contract/identity failures block writes and preserve pending work. [Compatibility](Docs/COMPATIBILITY.md) owns policy and daily upstream probes.

CAC finds a native `codex.exe` on `PATH`, in the standard Desktop installation, or behind the npm launcher. Set `codex_executable` in settings for another absolute native EXE path. CAC never updates, pins or downgrades your Codex installation.

The EXEs are unsigned. Windows may display a reputation warning. Verify the download and its provenance; this project does not provide a code-signing certificate.

## Controls and settings

Double-click the icon or select `Read Full Status` for a dark status panel with current state, usage and waiting thread names. The compact menu shows 5-hour and 7-day capacity remaining; Full Status labels the percentages explicitly. Missing readings say Unavailable; retained readings are marked Last Known in Full Status.

The arrow is green when monitoring with no pending work, yellow while work is pending, gray when stopped or reconnecting, and red when attention is required. Up to four yellow stack layers show the number of unique pending threads, including while stopped. Selected menu options have a tinted row and a small right-edge marker, separate from hover highlighting. `Exit CAC` stops the supervisor before closing the tray.

Use the tray to select clients, edit the prompt and settings, choose Private or Detailed logging, and toggle login launch. The companion terminal controls the same supervisor and saved settings:

```powershell
.\CodexAutoContinuer-CLI.exe status
.\CodexAutoContinuer-CLI.exe scan
.\CodexAutoContinuer-CLI.exe --help
```

`scan` reports its completed counts and can send an eligible continuation; it is not a preview. `stop` finishes the current cycle and preserves pending work. The [short user guide](Docs/USER-GUIDE.md) covers every menu action, terminal diagnostics and moving a used copy. It is shipped beside the EXEs with the runtime, licenses and checksums, not developer docs or audits.

`Modify Settings` opens `data/settings.toml`, creating a commented template if missing. Built-in defaults apply without a file. Uncomment only values you want to override:

```toml
clients = ["cli", "desktop"]  # Monitor these clients; [] pauses client monitoring.
poll_seconds = 30.0  # Seconds between scans.
detailed_telemetry = true  # Retain real metadata locally, never conversation bodies.
```

Tray changes preserve comments. Valid edits apply between cycles without restarting. Invalid settings or an empty, invalid or unreadable prompt pause continuation until repaired, preserving pending work. Files open asynchronously in their associated editor, or Notepad if no association exists.

`Restore Defaults` preserves the selected prompt and its content, pending state, existing logs and login shortcut. Future logging returns to Private; existing files are not deleted.

## Client coverage

Local interactive CLI, VS Code extension and Desktop sessions are selected by default. Each can be enabled independently. They must share the same native Codex home and account. `codex exec`, sub-agents, unknown sources and explicit `appServer` sources are excluded. Other app-server sessions reporting `vscode` use the VS Code bucket unless their originator identifies Desktop; this is client provenance, not proof of an open UI.

Shared internals do not guarantee shared chats: clients may use different homes, accounts or app-server processes. CAC checks the exact active writer and uses Codex's shared queue without stealing ownership. [Native research](Docs/RESEARCH.md) records the tested recovery path and source-filter rules.

Remote, cloud, WSL, different Windows users, different `CODEX_HOME` directories and different accounts are not automatically covered. Real CLI queue delivery and Desktop-owned server delivery have native evidence. An installed VS Code extension's native owner also passed isolated filtering and quota-recovery tests. [One natural Desktop recovery](Docs/History/2026-10-04-natural-recovery.md) was observed; visual chat rendering and universal client coverage are not established by those checks.

## Recovery policy

The latest turn must be `failed` with structured `usageLimitExceeded`. A network error, approval, user-input wait or interrupted task is not eligible. The discovery window is 24 hours from failure completion, including failures before launch. Once recorded, an obligation remains durable beyond that window.

Reset timestamps are hints, not permission. Only `ordinaryUsageAllowed == true` authorizes dispatch. CAC re-checks the exact failed turn immediately before sending. Manual progress cancels stale work and deletes only CAC's still-queued message.

The queue has no verified atomic turn precondition or idempotent-send guarantee. A narrow concurrent-progress race remains. An ambiguous send is reconciled, never blindly retried. Do not delete `state.json` to force a retry. See [the safety model](Docs/ARCHITECTURE.md).

## Local telemetry and privacy

Queue holding is experimental, off by default and not exposed in the tray. Its existing engine, encrypted data and [CLI review controls](Docs/USER-GUIDE.md#experimental-queue-holding) remain available. It does not protect normal Desktop, extension or CLI composers. Client integration is [deferred work](Docs/PRODUCT.md#deferred-client-queue-integration); the [installed-client investigation](Docs/Audits/History/2026-10-05/AUDIT.md) records the evidence. Ordinary quota recovery remains independent of holding.

Held input and attachments are an explicit privacy exception: only this opt-in feature stores their canonical payload, encrypted locally for the Windows account and bound to the Codex home/account. No full conversation archive, telemetry bodies or diagnostic uploads are created. A used encrypted journal is not portable to another person's account; share the clean release instead.

There is no remote analytics or diagnostic upload. The [signed updater](Docs/UPDATES.md) requests GitHub releases every 6 hours without sending chat data. Set `auto_update = false` for manual updates. The repository is private during testing; public sharing will not require a GitHub login. Codex's own network traffic and telemetry are separate.

Beside the EXEs, `data/` holds settings, prompt, pending state, local status and compact JSONL logs. Logs retain quota failures, recovery decisions, dispatch results, subsequent-turn observations and RPC timings so a later investigation can follow an entire recovery.

Private mode omits names and paths and uses keyed identifiers. Detailed mode retains real identifiers, chat names and paths. Neither records conversation bodies, prompt text, credentials, raw RPC payloads or exception locals. Each stream defaults to 8 MiB plus three gzip backups. `diagnostic_trace` adds allowlisted request summaries. Settings comments explain retention and tracing.

Ordinary logs and state are not encrypted; the optional held-input journal is encrypted separately. Switching to Private affects future events, not old detailed logs. Private logging does not anonymize pending state or user-authored settings and prompts. Share the clean release ZIP, not a used `data/` folder. See [safe reporting](SECURITY.md) before attaching diagnostics.

Small per-user coordination files prevent competing portable copies. A pip-installed CLI controls the last registered app copy. Source checkouts use `.data/runtime`; portable EXEs use adjacent `data`. A clean release starts with Private logging and no obligations.

## Why this design suits us

The survey below was checked on 3 October 2026. It describes documented approaches, not a benchmark or a claim to have found every existing tool.

| Tool | Documented approach | Why ours fits this workflow |
| --- | --- | --- |
| [codex-charge](https://github.com/Autumnpoem/codex-autocontinue) | CLI terminal wrapper; Desktop focus and clipboard submission; tray controls | We want existing local chats across clients without changing focus or the clipboard |
| [MrPanica watchdog](https://github.com/MrPanica/codex-auto-resume) | Windows UI Automation invokes retry controls; covers several transient errors | We want structured quota-only recovery, independent of UI controls |
| [progressrdx auto-resume](https://github.com/progressrdx/codex-auto-resume) | macOS companion with selected-task fingerprints and bounded continuation | Similar conservative targeting; ours is Windows-native and covers local interactive clients |
| [auto-resume-trio](https://github.com/awslew/codex-auto-resume-trio) | Same-session CLI/app-server recovery with host and project/quota dashboards | Similar structured approach; we prefer one portable tray folder over several services |
| [Claude Codex Queue](https://github.com/ravhello/claude-codex-queue) | Ordered prompt queues, existing tasks, web and CLI controls; Windows setup uses WSL | We need a narrower native Windows recovery tool, not a full prompt-queue workflow |
| [claude-codex-auto-resume](https://github.com/TheOnlyFusionCube/claude-codex-auto-resume), [automode](https://github.com/adrielmendes28/automode) | Multi-tool terminal wrappers that parse usage/reset messages | Useful for wrapped terminals; ours watches structured state without requiring a launch wrapper |
| [Codex Dashboard](https://github.com/Justin1491/codex-dashboard) | Usage dashboard with project auto-resume through `codex exec resume --last` | We require exact failed interactive chats and deliberately exclude executor jobs |
| [Perpetual](https://github.com/SakethSripada/Perpetual) | VS Code orchestration, provider switching, cloud handoff and Docker | We want to stay on the original Codex task and wait for authorized usage |
| [rate-tray](https://github.com/nowrap/rate-tray), [Codex Companion](https://github.com/heycarollan/codex-usage-status), [Limit Reset Tracker](https://codexlimitreset.com/) | Usage displays, alerts or countdowns rather than this exact recovery policy | We need automatic exact-chat continuation as well as visibility |

Our preference is about fit: native Windows, existing interactive chats, exact-thread checks, no UI input, editable Markdown and local diagnostics. Other tools can suit different users. Experimental queue dependence is our main tradeoff.

## Development and repository layout

[Contributing](CONTRIBUTING.md) covers isolated Python setup, Windows verification, source launch and release build. Verification CI builds clean candidates. The separate signed-release workflow publishes tested stable releases from tags or manual dispatch.

[Native continuation tests](Docs/CONTINUATION-TESTS.md) exercise the installed Codex executable and CAC recovery engine against local quota and response fixtures. No real login, account exhaustion or user-chat continuation is needed. This proves the controlled native recovery chain, not a natural service reset or every client UI.

`src/` owns runtime code and the [SVG icon](src/codex_auto_continuer/assets/cac.svg); `tests/` owns product regressions; `scripts/` owns build and verification tools. [Docs](Docs/README.md) links the user guide, technical contracts and dated evidence. Audit history and the ChatGPT/Codex manifests are tracked development records, not runtime requirements or downloadable-app contents.

Our code uses the [MIT license](LICENSE). See [dependency notices](Docs/THIRD-PARTY.md). Runtime data, deployed apps, virtual environments and build output remain local and are excluded from source transports.
