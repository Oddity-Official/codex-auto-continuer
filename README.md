# Codex Auto Continuer

A Windows-native supervisor that resumes the exact Codex Desktop thread that stopped on a structured usage-limit failure. It sends a continuation only after Codex confirms ordinary usage is available.

It talks directly to Codex's shared local app-server using structured thread, turn, queue and rate-limit RPCs. It does not click windows, inject keys, use the clipboard, scrape the screen, or guess which Codex window is focused.

## Requirements

- Windows 11
- Python 3.13
- PowerShell 7 on `PATH`
- Codex CLI 0.160.0 or newer on `PATH`
- The same Codex account/session used by Codex Desktop

Native Windows checks and live Codex 0.160.0 integration passed on 3 October 2026. See [verification and limits](Docs/VALIDATION.md). A real quota failure, waiting period and stale cancellation after manual resume were observed. Automatic continuation at natural quota recovery has not yet been observed.

## Install

From the project root:

```powershell
py -3.13 -m pip install .
codex-auto-continuer init
codex-auto-continuer status
```

The default config is written under `%LOCALAPPDATA%\CodexAutoContinuer\config.json`. Edit `continue_prompt` there to change the continuation text. The default discovery window is 24 hours, measured from the failed turn's completion. Recorded obligations survive restarts and keep waiting beyond that discovery window.

Start or stop the hidden background process:

```powershell
codex-auto-continuer start
codex-auto-continuer status
codex-auto-continuer stop
```

`stop` finishes the current scan/dispatch cycle and preserves pending obligations. `status` reports `supervisorRunning` using the operating-system instance lock, rather than trusting a stale PID file. Restart the process after editing its config.

Run it in the foreground:

```powershell
codex-auto-continuer run
```

Run one scan/dispatch cycle for diagnosis:

```powershell
codex-auto-continuer once
```

Install the per-user login shortcut, then start it now:

```powershell
codex-auto-continuer install-startup
codex-auto-continuer start
```

Stop the current process and remove only this project's managed login shortcut:

```powershell
codex-auto-continuer stop
codex-auto-continuer uninstall-startup
```

For a non-default config file, put the global option before the command, for example:

```powershell
codex-auto-continuer --config D:\Config\codex-auto-continuer.json run
```

## Safety model

The supervisor records an obligation only when the latest turn is `failed` with structured `codexErrorInfo = usageLimitExceeded`. Reset timestamps are advisory; dispatch is gated by `account/rateLimits/read.ordinaryUsageAllowed == true`. Before dispatch it re-reads the exact thread and failed turn. If the thread advanced, the obligation is stale and is cancelled. If this tool already has a still-queued continuation, that exact queue item is deleted as part of stale cancellation.

Desktop scope accepts the verified `vscode` source with `Codex Desktop` originator, plus the configured `chatgpt` and `atlas` custom sources. It excludes ordinary VS Code extension, CLI, executor and sub-agent sessions by default.

The durable state stores thread/turn IDs, timestamps, deterministic client message IDs, dispatch phase and queue IDs. It does not store conversation bodies. Ambiguous submissions are never retried blindly. If neither a queued submission nor an advanced turn can be verified, the process stops rather than risk a duplicate continuation.

Logs are under `%LOCALAPPDATA%\CodexAutoContinuer\auto-continuer.log`, with 2 MiB per file and 2 backups. Server error bodies are excluded. If the process stops on a protocol or state error, inspect the log and resolve the cause before restarting. Do not delete the state file to force a retry.

All commands also work as `py -3.13 -m codex_auto_continuer ...` if Python's Scripts directory is not on `PATH`.

## Build and verify

```powershell
py -3.13 -m pip install '.[dev]'
pwsh -NoProfile -File scripts/verify-windows.ps1
py -3.13 -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

The wheel is `dist/codex_auto_continuer-0.1.0-py3-none-any.whl`. The source handoff is produced by `scripts/pack-codex-handoff.ps1`. Build output and per-user runtime data are excluded from that handoff.

See [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md), [Docs/RESEARCH.md](Docs/RESEARCH.md), and [Docs/VALIDATION.md](Docs/VALIDATION.md).
