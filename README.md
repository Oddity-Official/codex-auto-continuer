# Codex Auto Continuer

A portable Windows tray tool that continues the exact Codex chat stopped by a usage limit. It waits until Codex confirms ordinary usage is available. No window clicking, clipboard changes, keystrokes or screen scraping.

This is an independent tool, not an OpenAI product. It uses experimental local Codex interfaces and stops with a diagnostic if their contract changes. See [verified behavior and limits](Docs/VALIDATION.md).

## Launch and use

1. Extract `codex-auto-continuer-0.2.1-windows-x86_64.zip` into a writable folder. Keep both EXEs and `_internal` together.
2. Launch `CodexAutoContinuer.exe`. Monitoring starts automatically. Look in Windows' hidden tray icons if needed.
3. Right-click the tray icon. Select `Start with Windows` to enable per-user login launch.
4. Select `Modify prompt` to open `data/continue-prompt.md` in your default Markdown editor. Save as UTF-8. The next continuation reads the saved file; no restart is needed.

The portable release needs Windows 11 x86_64 and a signed-in native Codex installation. It bundles Python and the tray dependencies. Recipients do not need Python, PowerShell 7, WSL or administrator privileges. Startup management can use Windows' built-in PowerShell.

Codex CLI and app-server 0.160.0 are the tested baseline. Newer versions must expose the same required capabilities. The tool finds `codex.exe` on `PATH`, the standard Desktop installation, or a native executable behind the npm launcher. Set `codex_executable` in settings for another absolute native EXE path.

The EXEs are unsigned. Windows may display a reputation warning. Verify your download and its provenance; this project does not provide a code-signing certificate.

## Tray and terminal controls

Double-click the icon for status. Green means monitoring, amber means pending recovery, grey means stopped and red means an error. Error notifications point you to settings and telemetry. `Quit (stop monitoring)` stops the supervisor before closing the tray.

The companion terminal program is `CodexAutoContinuer-CLI.exe`. The menu and CLI control the same supervisor and saved settings:

| Tray action | Terminal command |
| --- | --- |
| Status | `status` |
| Start, stop or restart monitoring | `start`, `stop`, `restart` |
| Scan now | `scan` |
| Run one cycle while stopped | `once` |
| Modify prompt | `modify-prompt` |
| Open settings or telemetry folder | `open-config`, `open-logs` |
| Show config location | `config-path` |
| Initialize missing files | `init` |
| Restore default settings, preserving prompt files and state | `init --force` |
| CLI, VS Code and Desktop; Desktop only | `scope allInteractive`, `scope desktop` |
| Detailed local telemetry toggle | `logging detailed`, `logging private` |
| Start with Windows toggle | `install-startup`, `uninstall-startup` |
| Open tray; show version | `tray`, `--version` |

`run` provides foreground monitoring for terminal diagnostics. It is the same monitoring engine, not a separate tray feature.

For example, from the extracted folder:

```powershell
.\CodexAutoContinuer-CLI.exe status
.\CodexAutoContinuer-CLI.exe scan
.\CodexAutoContinuer-CLI.exe --config 'D:\My settings\config.json' status
```

`scan` wakes a running supervisor; while stopped it performs one cycle. `stop` finishes the current cycle and preserves pending obligations. Scope and privacy commands restart a running supervisor. After manually editing other JSON settings, use `Restart monitoring`. An empty, invalid or unreadable prompt stops dispatch rather than substituting different text.

## Which Codex clients are covered

The default scope includes local interactive CLI, VS Code extension and Desktop sessions visible to the same native Codex home and account. It excludes `codex exec`, sub-agents, arbitrary app-server sessions and unknown sources. Desktop-only mode checks the verified `vscode` plus `Codex Desktop` originator pair, or configured Desktop custom sources.

Shared Codex internals are not enough by themselves. Clients can own separate app-server processes. We verify the exact active-writer condition and use Codex's shared queue without stealing ownership. [Official app-server documentation](https://learn.chatgpt.com/docs/app-server) describes the shared integration layer; [our native probes](Docs/RESEARCH.md) establish the recovery path on the tested installation.

Remote, cloud, WSL, different Windows users, different `CODEX_HOME` directories and different accounts are not automatically covered. Real CLI queue delivery and Desktop-owned server delivery have native evidence. VS Code filtering is tested, but the actual extension UI was not available for an end-to-end test.

## Recovery policy

The latest turn must be `failed` with structured `usageLimitExceeded`. A network error, approval, user-input wait or interrupted task is not eligible. The discovery window is 24 hours from failure completion, including failures before launch. Once recorded, an obligation remains durable beyond that window.

Reset timestamps are hints, not permission. Only `ordinaryUsageAllowed == true` authorizes dispatch. We re-read the exact thread and failed turn immediately before sending. Manual progress cancels the obligation and deletes only this tool's still-queued message.

The queue has no verified atomic turn precondition or idempotent-send guarantee. A narrow concurrent-progress race remains. An ambiguous send is reconciled, never blindly retried. Do not delete `state.json` to force a retry. See [the safety model](Docs/ARCHITECTURE.md).

## Local telemetry and privacy

There is no remote analytics, upload endpoint or automatic updater. This tool writes local JSONL telemetry: one JSON event per line. Codex's own network traffic and telemetry are separate.

Beside the EXEs, `data/` holds settings, Markdown prompt, durable state, runtime status, `telemetry.jsonl`, `tray.jsonl` and a private identifier-correlation key. Events capture process/version information, settings, RPC methods and duration, quota snapshots, discovery decisions, failed-turn metadata, revalidation, queue ownership, dispatch intent and result, cancellation, reconnection, errors and subsequent turn outcomes. Error diagnostics contain exception types and stack locations, not arbitrary server error text.

The default private mode omits chat names and filesystem paths from telemetry. Thread, turn and queue identifiers become stable keyed pseudonyms, so events remain traceable within one installation. Detailed mode retains real identifiers, chat names and paths. Neither mode records conversation bodies, prompt contents, authentication tokens, credentials, raw RPC payloads or exception locals. A prompt hash and length identify which saved prompt was used. Numeric token-usage notifications are retained when available.

Default retention is 16 MiB per stream plus 8 rotated backups: up to about 144 MiB each. `log_max_mb` and `log_backups` are configurable. Switching to private mode affects future events; it does not scrub older detailed logs. These files are not encrypted.

Private telemetry is not an anonymized installation: `state.json` needs real IDs to target chats, and settings and the prompt are user-authored. Do not share the whole used `data/` folder without inspecting it. Share the clean release ZIP instead. Builds exclude all runtime data.

Each account also has small coordination files under `%LOCALAPPDATA%\CodexAutoContinuer`. These prevent two portable copies from monitoring simultaneously. A pip-installed CLI controls the last registered app copy. Source checkouts use `.data/runtime`; portable EXEs use their own adjacent `data` folder.

To move a used copy, quit first, move the entire folder with `data`, then launch from the new location. Reinstall its login shortcut. A new clean release starts with private logging and no obligations.

## Why this design suits us

The public survey below was checked on 3 October 2026. It describes each project's documented approach, not a benchmark or a claim to have found every existing tool.

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

Our preference is about fit: native Windows, existing interactive chats, exact-thread checks, no UI input, editable Markdown and local diagnostics. It is not a claim that other tools are worse for every user. Experimental queue dependence is our main tradeoff.

## Source install and build

For source development, use Python 3.13 and PowerShell 7. Build in an isolated virtual environment:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install '.[dev,build]'
pwsh -NoProfile -File scripts/verify-windows.ps1
pwsh -NoProfile -File scripts/build-portable.ps1
.\.venv\Scripts\python.exe -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

The native gate uses the configured `py -3.13` interpreter; install `.[dev]` there too if it lacks test dependencies. Source commands work as `python -m codex_auto_continuer ...` after installation. `python -m codex_auto_continuer tray` provides the same tray UI.

The portable builder creates a clean folder release, dependency notices and source, a per-file SHA-256 manifest and a verified ZIP. It never copies deployed runtime data. One-folder packaging avoids a self-extracting runtime on every launch and keeps tray libraries replaceable. [PyInstaller operating modes](https://pyinstaller.org/en/stable/operating-mode.html) explain this tradeoff.

The wheel is `dist/codex_auto_continuer-0.2.1-py3-none-any.whl`. The stable source handoff is `codex-auto-continuer-codex-handoff.zip`, produced by `scripts/pack-codex-handoff.ps1`. Our code uses the [MIT license](LICENSE). See [dependency notices](Docs/THIRD-PARTY.md) and [the documentation index](Docs/README.md).
