# Product contract

## Goal

Automatically resume Codex Desktop work that stopped specifically because account usage was exhausted, without requiring the user to remember the reset time or manually send `Continue`.

## Required behavior

- Target the exact Codex thread that stalled, never whichever window happens to be focused.
- Use structured Codex thread/session state and first-party CLI/app-server interfaces. Do not rely on clipboard, focus stealing, keystroke injection, screen scraping or window-title matching.
- Detect usage exhaustion as a distinct condition from network failures, server overload, policy blocks, approvals, user-input waits and unrelated failed turns.
- Associate a continuation obligation with the exact failed thread/turn and its relevant reset window.
- Revalidate immediately before continuing. If the user or another client has already advanced the thread, cancel the stale obligation instead of sending a duplicate message.
- Support more than one stalled thread without cross-thread mixups or duplicate dispatch.
- Make the continuation prompt user-configurable without source edits.
- Discover failures completed in the last 24 hours and new failures during operation. Keep recorded obligations until resolved, even beyond the discovery window.
- Support hidden per-user login launch, explicit background start/stop, and observable running status.
- Fail loudly and diagnostically when Codex interfaces change or required state cannot be verified. Do not silently fall back to UI automation.
- Keep durable state minimal, explicit and non-secret. Avoid storing conversation bodies unless a verified design need appears.
- Target native Windows 11 and PowerShell 7. WSL must not be required.

## Non-goals

- General-purpose desktop macro automation.
- Circumventing Codex usage limits or causing model work before usage is available.
- Automatically resolving approvals, security prompts or explicit requests for user input.
- Treating every failed/interrupted turn as eligible for automatic continuation.
- Backward-compatibility layers for undocumented Codex interfaces unless a concrete supported version needs them.

## Current phase

Version 0.1.0 is validated for native use with Windows 11, PowerShell 7, Python 3.13 and Codex 0.160.0. Current checks and remaining observational limits belong to [VALIDATION.md](VALIDATION.md).
