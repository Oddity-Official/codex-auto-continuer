# Codex Auto Continuer

A small Windows-native supervisor that resumes the **exact Codex Desktop thread** that stopped on a verified usage-limit failure, but only after Codex reports ordinary usage is available again.

It talks directly to Codex's shared local app-server using structured thread, turn, queue and rate-limit RPCs. It does not click windows, inject keys, use the clipboard, scrape the screen, or guess which Codex window is focused.

## Requirements

- Windows 11
- Python 3.13
- Codex CLI 0.160.0 or newer on `PATH`
- The same Codex account/session used by Codex Desktop

Native Windows validation is still required before this checkpoint is considered release-ready. Linux tests validate the platform-independent state machine, protocol framing and workflow, not Windows AF_UNIX or Startup behavior.

## Install

From the project root:

```powershell
py -3.13 -m pip install .
codex-auto-continuer init
codex-auto-continuer status
```

The default config is written under `%LOCALAPPDATA%\CodexAutoContinuer\config.json`. Edit `continue_prompt` there if you want different continuation text.

Run it in the foreground:

```powershell
codex-auto-continuer run
```

Run one scan/dispatch cycle for diagnosis:

```powershell
codex-auto-continuer once
```

Install an unobtrusive per-user Startup launcher:

```powershell
codex-auto-continuer install-startup
```

Remove only the launcher managed by this project:

```powershell
codex-auto-continuer uninstall-startup
```

For a non-default config file, put the global option before the command, for example:

```powershell
codex-auto-continuer --config D:\Config\codex-auto-continuer.json run
```

## Safety model

The supervisor records an obligation only when the latest turn is `failed` with structured `codexErrorInfo = usageLimitExceeded`. Reset timestamps are advisory; dispatch is gated by `account/rateLimits/read.ordinaryUsageAllowed == true`. Before dispatch it re-reads the exact thread and failed turn. If the thread advanced, the obligation is stale and is cancelled. If this tool already has a still-queued continuation, that exact queue item is deleted as part of stale cancellation.

The durable state stores thread/turn IDs, timestamps, deterministic client message IDs, dispatch phase and queue IDs. It does not store conversation bodies. Ambiguous post-crash submissions are **not retried blindly**: if neither a queued submission nor an advanced turn can be verified, the process fails loudly rather than risk a duplicate continuation.

See [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md), [Docs/RESEARCH.md](Docs/RESEARCH.md), and [Docs/VALIDATION.md](Docs/VALIDATION.md).
