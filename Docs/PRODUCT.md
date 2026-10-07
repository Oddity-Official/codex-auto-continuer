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
- support optional per-user Windows login launch and automatic monitoring start without administrator rights or WSL; historical failures must not veto a fresh start
- keep runtime data beside the app or source checkout; coordinate one supervisor and one tray across app copies
- write bounded local metadata telemetry with private defaults and explicit detailed mode
- never store conversation bodies, credentials, raw request payloads or exception locals in telemetry
- preserve submitted-delivery observations across restart, without claiming a later turn necessarily came from our message
- block diagnostically on unsupported identity, protocol drift or unreadable prompts; isolate ambiguous sends without retries while other safe chats continue
- default to Balanced compatibility for schema-verified stable Codex builds; offer Strict exact-build certification and deduplicated warnings
- update portable CAC from signed stable GitHub releases at cycle boundaries, preserving runtime data and a recoverable code backup
- keep experimental owner-supported holding off by default and outside the tray; preserve its encrypted data and CLI review controls

## Non-goals

- bypassing account limits, switching accounts or providers, or spending credits before ordinary usage is allowed
- automatically answering approvals, security prompts, tool elicitations or explicit user-input requests
- resuming arbitrary network failures, interrupted work, CI jobs or sub-agents
- monitoring remote, cloud or WSL sessions outside the visible native Codex home
- uploading telemetry, collecting credentials or maintaining a remote analytics service
- supporting unverified queue retry or atomicity guarantees
- trusting unknown Codex builds without identity, schema and runtime checks, or modifying Codex's installation/update policy

## Supported release

Version 0.7.0 targets Windows 11 x86_64. Balanced mode permits unknown stable builds only after identity, schema and runtime checks; Strict mode additionally requires an exact recovery certificate. [Compatibility](COMPATIBILITY.md) owns that policy. [Updates](UPDATES.md) owns signed CAC releases and rollback. The portable release bundles Python, a short guide and dependency notices, not developer docs or audit history. Source development uses Python 3.13 and PowerShell 7. Current results and limits belong to [VALIDATION.md](VALIDATION.md).

## Approved tray and status refinement

This is the consolidated interface contract, approved on 4 October 2026 with later user decisions. The source implementation uses native owner drawing. Current acceptance checks and delivery limits belong to [verification](VALIDATION.md). Presentation must not change recovery decisions or the saved continuation prompt.

### Rendering approach

Use an owner-drawn Win32 `HMENU`: compact dark rows and custom header rendering inside the native Windows menu loop. The architecture owner records the alternatives and their interaction costs.

The current pystray adapter owns the native menu for the whole tracking operation. Preserve that lifetime rule: background updates and callbacks must not replace a menu while Windows is tracking it.

Keep dark-only rows and submenus, no checkmark gutter, tight padding, persistent selected backgrounds, distinct hover styling, meters, custom header layout and readable disabled states. Check borders and submenu arrows too. Do not rely on undocumented theme hacks or silently compromise these requirements.

If a custom popup is necessary, account for keyboard navigation, Enter and Escape, submenu navigation, mouse hover/click, outside-click dismissal, activation/focus, taskbar edges, multiple monitors, DPI, work-area clamping, disabled items and practical accessibility. Styling convenience alone does not justify interaction regressions.

Keep the chosen architecture in `ARCHITECTURE.md`, not another competing design document. Preserve accessible text names and states even when painting rows manually.

### Compact menu

The menu is always dark charcoal or near-black, regardless of Windows theme. Deliberately style text, disabled states, separators, selected rows, hover rows and submenu arrows. There is no light variant.

```text
Waiting For Usage • 1 Thread
5H: <remaining-capacity meter> 73% • 3:42 PM
7D: <remaining-capacity meter> 41% • Oct 7
Read Full Status
---
Start Monitoring
Stop Monitoring
Clients To Monitor >
    VS Code
    CLI
    Desktop
    All
Start With Windows
---
Modify Prompt
Modify Settings
Open Data Folder
Telemetry >
    Detailed
    Private
Restore Defaults
---
Check For Updates
About CAC <current version>
Exit CAC
```

Use graphical meters rather than literal block characters when the renderer supports them. Keep the header compact, not dashboard-sized. Do not add `Left` or `Remaining` to the compact percentages. Full Status explicitly explains the semantics. Source the version dynamically.

While monitoring, disable Start and enable Stop; reverse these states when stopped. Disabled text must remain readable. Keep existing confirmations, file actions, updater behavior and graceful exit.

Remove all native checkbox/radio marks and the wide left gutter, including in submenus. Show persistent selection with a muted accent background plus a small upright rectangle at the right edge, taller than it is wide. Use a brighter, distinct hover treatment. Do not add literal brackets, `On` or `Selected` labels. Preserve programmatic selected/checked accessibility states without rendering native checkmarks. Reclaim the gutter and excessive horizontal padding to make the menu narrower.

### State wording and counts

Use concise title-case interface text and correct singular/plural wording. Count unique unresolved continuation obligations, not events, failed turns or historical delivery observations.

| Condition | Header |
| --- | --- |
| Monitoring, no unresolved obligations | `Monitoring` |
| Quota unavailable, unresolved obligations | `Waiting For Usage • 1 Thread` or `Waiting For Usage • 3 Threads` |
| Dispatch or reconciliation underway | `Resuming • 2 Threads` |
| Intervention or blocking issue | `Needs Attention`, with affected thread count when useful |
| Stopped or paused | `Stopped`; retain pending information in the icon and status window |

Do not use vague wording such as `1 waiting`. Derive presentation from canonical application state, not an independent UI state machine. Clear the stack count when an obligation resolves, even if later telemetry still observes the resulting turn. Starting and reconnecting need honest transient labels, not healthy green.

### Usage presentation

Verify fields and meaning against the actual upstream contract. Identify 5-hour and 7-day windows by duration, not by assuming primary/secondary order. Select the authoritative ordinary Codex quota bucket, not an arbitrary model-specific limit. For valid known `usedPercent`, remaining capacity is `100 - usedPercent`. Fuller meters mean more remaining capacity.

Show percentage and reset independently if only one is available. Display an explicit unknown/unavailable state for missing data. Distinguish fresh readings from last-known readings after stop, disconnect or service failure. Do not fabricate a reset, infer it from a percentage, or infer dispatch permission from either. `ordinaryUsageAllowed == true` remains the sole usage permission authority.

Use the user's local timezone. Normally show a local clock time for the 5-hour reset and a compact date such as `Oct 7` for the 7-day reset. Add date, time or year when necessary to avoid ambiguity. Full Status says `73% Remaining`. Start with static meters. Any later idle animation must not imply changing quota and must stop entirely when the popup closes.

### Dynamic icon

Keep the off-white stack legible at actual Windows tray sizes. Arrow color and stack count are independent.

| Arrow | Meaning |
| --- | --- |
| Green | Monitoring normally, zero unresolved obligations |
| Yellow | Monitoring with unresolved obligations, including quota waiting or recovery underway |
| Gray | Stopped, paused, starting or reconnecting |
| Red | Error or intervention-required state; highest precedence |

Turn 0, 1, 2, 3 or all 4 stack layers yellow for 0, 1, 2, 3 or at least 4 unique pending threads. Use one consistent progression order. Preserve pending layers while stopped. Red may indicate an isolated unconfirmed send even while other safe chats continue; it does not claim every chat has stopped. An untested Balanced-compatible build alone is not an error.

Generate or render variants from the SVG master. Inspect realistic 16px, 20px, 24px and 32px output, not only large artwork.

### Full Status window

Replace the dense native status message box with a compact dark window. Its hierarchy is current state, usage, then waiting threads. Align labels and values and keep information grouped.

Current state includes human-readable status, selected clients and last scan. Retain a compact compatibility summary (`Verified`, `Untested` or `Blocked`, with Balanced/Strict policy) and update state. Expose exact version details and failure explanations through a lightweight details affordance. Blocking issues need a specific reason and useful next action, not only `Needs Attention` or advice to inspect logs.

Do not carry over counters such as chats checked, failures or continuations sent without a clear user need and scope. Do not duplicate telemetry mode here.

Each usage row includes a remaining-capacity meter, an explicit remaining percentage and a local reset. Preserve unknown and freshness distinctions.

Waiting threads are first-class information. Show only an authoritative Codex name/title; never derive it from preview or conversation text. Use `Untitled Thread` when the source confirms no name. Distinguish a failed/unavailable name lookup from a genuinely unnamed thread. Raw UUIDs are secondary diagnostics, not primary display names.

Use a primary title with a smaller secondary reason where useful:

```text
Story Linter - Performance Pass
Waiting For Usage

Untitled Thread
Send Unconfirmed - Checking Whether Codex Accepted It
```

Other useful reasons include `Reconciling`. Explain actionable ambiguity without claiming acceptance or retrying it.

Ellipsize long names within a fixed reasonable width; offer a full-title tooltip or lightweight detail affordance. Hide the entire waiting section when empty and shrink the window. For many threads, scroll only that section instead of growing the window without bound.

Fetch required names asynchronously and keep them in memory for the status view. Opening status must not block the UI, resume a chat or subscribe to its work. No focus manipulation may be used to perform recovery. Do not persist names solely for UI, particularly in the on-disk Private status snapshot. Preserve existing explicit Detailed telemetry behavior.

### Reliability and verification

Preserve exact-thread targeting, quota-only recovery, crash reconciliation, multi-client behavior, privacy, no clipboard/UI-input fallback and diagnostic contract checks. Preserve Balanced versus Strict compatibility behavior, isolated ambiguous sends and signed updates. Keep the saved prompt exactly as written, defaulting to `Continue`; no recovery wrapper.

Meaningful checks must cover singular/plural counts; 0/1/2/3/4/more pending icons; all arrow states and precedence; stopped-with-pending; selected versus hover versus disabled rows; no checkmark gutter; usage semantics, partial unknowns and stale readings; long/absent/unavailable titles; dynamic version; dark layout and accessibility names/states. Existing continuation/recovery regressions must remain green.

Run the native Windows gate and inspect actual popup, submenus, icons and status window under light/dark Windows themes and representative DPI settings. Check keyboard-only navigation, Enter/Escape, submenu traversal, outside-click dismissal, repeated opening and state changes while a menu is open. A unit-test-only pass is insufficient. Application-rendered images do not prove mouse/keyboard behavior. If native computer-control tools remain unavailable, record that limit and obtain the user's hands-on inspection rather than claiming it occurred.

## Deferred client queue integration

Queue holding remains experimental and is not exposed in the tray. Preserve the engine, encrypted journal, CLI review controls and native probe evidence. Do not add transport adapters, patch Codex or promise normal composer coverage as part of the interface work.

Revisit only with an explicit user request. Acceptance requires pre-consumption capture through each actual Desktop, VS Code and CLI composer, unchanged Continue, ordered exactly-once follow-up handling and restart/uncertainty checks. Server-RPC fixtures and connection proofs alone do not meet this requirement. CLI's client-local queue needs its own integration boundary. See the [installed-client investigation](Audits/History/2026-10-05/AUDIT.md).
