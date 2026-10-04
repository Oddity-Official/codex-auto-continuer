# Product contract

## Goal

Continue existing local interactive Codex tasks after account usage recovers, without asking the user to remember reset times. Make the tool easy to launch, control, inspect and share on native Windows.

## Required behavior

- target the exact chat and failed turn, never the focused window or the latest project session
- use structured first-party Codex state; no clipboard, keystrokes, screen scraping or UI automation
- recognize only failed turns with structured `usageLimitExceeded`
- dispatch only after `ordinaryUsageAllowed == true`, with an immediate exact-thread and quota recheck
- cancel stale obligations after manual progress, deleting only our own remaining queue items
- cover local interactive CLI, VS Code and Desktop by default; exclude executor and sub-agent sessions
- offer independent CLI, VS Code and Desktop selection using source and originator provenance
- discover failures completed during the last 24 hours, including pre-launch failures; preserve recorded obligations beyond lookback
- re-read a UTF-8 Markdown prompt immediately before each send; open it in the default associated editor
- provide a concise native tray menu for everyday controls, local last-scan status, responsive repair actions, owned dialogs and graceful quit; retain diagnostic commands in the CLI
- use annotated TOML overrides, built-in defaults when absent, comment-preserving edits and validated hot reload at cycle boundaries
- ship a portable Windows x86_64 folder containing GUI and console EXEs, dependencies, notices and a checksum manifest
- support optional per-user Windows login launch without administrator rights or WSL
- keep runtime data beside the app or source checkout; coordinate one supervisor and one tray across app copies
- write bounded local metadata telemetry with private defaults and explicit detailed mode
- never store conversation bodies, credentials, raw request payloads or exception locals in telemetry
- preserve submitted-delivery observations across restart, without claiming a later turn necessarily came from our message
- stop diagnostically on unsupported versions, protocol drift, unreadable prompts or ambiguous sends; never silently substitute a guessed recovery path

## Non-goals

- bypassing account limits, switching accounts or providers, or spending credits before ordinary usage is allowed
- automatically answering approvals, security prompts, tool elicitations or explicit user-input requests
- resuming arbitrary network failures, interrupted work, CI jobs or sub-agents
- monitoring remote, cloud or WSL sessions outside the visible native Codex home
- uploading telemetry, collecting credentials or maintaining a remote analytics service
- supporting unverified queue retry or atomicity guarantees

## Supported release

Version 0.3.0 targets Windows 11 x86_64 and Codex 0.160.0-compatible local interfaces. The portable release bundles Python, a short user guide and dependency notices, not developer docs or audit history. Source development uses Python 3.13 and PowerShell 7. Current results and limits belong to [VALIDATION.md](VALIDATION.md).
