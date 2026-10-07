# Codex Auto Continuer audit

Audit date: 2026-10-07
Started at: 2026-10-07T11:35:31.757824+00:00

## Scope and boundary

Implement the approved tray/status presentation, remove experimental queue holding from everyday controls, and inspect recent production recovery/notification metadata. The source baseline was commit `8f4fcfa`; the installed release is CAC 0.6.1. Windows 11 x86_64, PowerShell 7, CPython 3.13.7 and the project virtual environment were used.

The user requested no further Computer Use while working. Isolated preview processes were stopped. No production monitor, installed binary, prompt, settings, startup shortcut or client profile was changed. No new release was built, uploaded or deployed. Source version remains 0.6.1 pending final interactive acceptance and versioned release checks.

## Implementation

- Owner-drawn native HMENU retains the Windows menu loop rather than recreating activation, keyboard navigation, dismissal and submenus. Documented menu-background, no-check-gutter and accessible-name structures provide dark compact rows, remaining-capacity meters and right-edge selected markers. Native interaction and border/submenu appearance still need acceptance.
- The separate native status panel groups current state, usage and waiting threads. Canonical durable obligations supply unique IDs/phases. A bounded asynchronous read-only lookup fetches authoritative names into view memory; no preview/body synthesis, resume, turn subscription or persistent title store is used. Long titles ellipsize; Details exposes the full name. The waiting list is bounded and scrollable; it is absent when empty.
- Twenty SVG-derived icon variants separate arrow status from zero-to-four yellow pending layers. The retained [actual-size sheet](icon-sizes.png) shows 16, 20, 24 and 32-pixel renders; generation uses [this helper](render_icon_evidence.py), not a screenshot or personal desktop capture.
- Experimental owner holding remains off by default in the CLI with encrypted journal/review/reconciliation tests. It has no tray submenu. The product owner records actual-client integration as deferred; no additional composer support is claimed.
- Transient runtime-status unreadability no longer implies recovery is blocked. Sharing errors get a 250-millisecond read budget; a persistent unavailable-status notice waits five seconds and explains that the independently running monitor's progress cannot be read. Configuration or durable-state errors remain actionable failures. Safe cause type/code and recovery duration are logged.

## Private telemetry review

Only sanitized event types, times, versions and outcomes are retained here. Raw logs, local paths, chat identifiers, names and conversation bodies are not copied into this report or source transport.

| Observation | Evidence | Interpretation and limit |
| --- | --- | --- |
| Natural continuation | 7 October, 10:09:40 UTC: separate-owner recovery intent and queue acknowledgement; 10:13:28 UTC: subsequent turn completed; no second submission for that obligation | Recovery was acknowledged and later progress observed. Subsequent-turn metadata is not proof that CAC alone caused that progress |
| Brief tray warnings | 5 October, 23:34:30 UTC and 7 October, 06:58:49 UTC: wrapped local runtime-status read failures while supervisor cycles continued | Old tray mapped read failure to failed status and a generic blocked-continuation notice. This fits the reported misleading warning. The old event did not record the underlying filesystem cause, so a sharing lock is not established as its cause |
| Quota-service outage | 7 October, 03:39:09 UTC: read-only quota RPC `-32603` followed by automatic retry | Existing recovery path handled unavailable permission without sending or losing pending work |
| Current compatibility | CLI 0.160.0, managed daemon 0.160.1, schema-verified untested Balanced tuple | Not the exact certified fixture tuple. Read/write permission under Balanced is distinct from exact certification |

The reviewed recent events showed no unresolved ambiguous send or lasting supervisor failure. This is a scoped observation, not a guarantee about every earlier run.

## Verification matrix

All commands ran from the project root with process-tree bounds through `scripts/run-project-command.ps1` or the normal integration wrapper. Native fixtures use unmodified official Codex 0.160.0, isolated homes and loopback synthetic account/model responses; they do not call a paid model or manipulate user chats.

| Check | Settings and bound | Result |
| --- | --- | --- |
| Final non-interactive Windows suite | `.venv/Scripts/python.exe -m pytest tests scripts/tests -q -k 'not about_dialog_closes'`; 180-second bound | 279 passed, 3 visible dialog cases deselected; 38.40 seconds |
| Native recovery/compatibility/holding | `scripts/verify-continuation.ps1 -CodexPath .data/ci-official-baseline/package/bin/codex.exe`; 240-second bound; wrapper resolves an absolute binary path | 18 passed; 110.44 seconds; certified CLI/daemon 0.160.0 tuple |
| Hidden Windows rendering | Included in the suite: actual native menu-owner subclass, measurement and GDI drawing at 96/144/192 DPI; selected/hover/disabled pixels; accessible names; no native check gutter; 73-percent meter endpoint and unknown meter | Passed without visible windows, foreground changes or Computer Use |
| State/privacy regressions | Included in the suite: unique count/pluralization, arrow precedence, stale/partial/unknown remaining quota, unrepresentable resets, completion between status/state reads, title fallback, read-only metadata lookup, Private ID protection, closed-view publication guard, transient/persistent warning and corrupt-state repair | Passed |
| Compilation | `python -m compileall -q src tests scripts integration Docs/Audits/2026-10-07`; 120-second bound | Passed |
| Markdown links | `python scripts/check-docs.py`; 30-second bound | 127 links; zero failures |
| Whitespace and changed-source privacy | Git whitespace check, scoped changed-source review and configured private-profile/credential patterns; export-boundary regressions included in the suite | Passed; no configured private-content matches |
| Source handoff inventory | Stable packer validates checksums; separate ZIP CRC, required-module/asset, excluded-tree and private-content inspection | 195 source payload files plus checksum manifest; all twenty icon variants present; no runtime/build trees, configured private-profile/credential markers or UUIDs found in the current private telemetry stream |
| Managed retention | `python scripts/manage-audits.py cleanup`; 30-second bound | Zero deletion targets; archived audit observations preserved |

The broad suite includes the existing recovery, locks, telemetry, signing/updating, privacy-boundary and workflow regressions. The three excluded tests create visible About dialogs. This run is not the full `verify-windows.ps1` gate.

The final read-only installed snapshot reported monitoring, zero pending obligations, CLI 0.160.0 and daemon 0.160.1 under untested Balanced compatibility. This validates current local status, not the uninstalled source UI. Source-handoff privacy inspection does not certify a newly frozen EXE; no new frozen build exists.

## Failed preliminary checks

- The first broad unit run had one obsolete asset expectation; the new twenty-variant regression replaced it. Final application checks passed.
- The first direct native invocation passed 14 cases and failed four. A relative executable path failed the absolute managed-binary identity check, and three holder fixtures referenced removed `monitoring.png`. The asset reference now uses `monitoring-0.png`; the documented wrapper resolves the path. Production identity guards were not relaxed. The final native gate passed.
- A hidden rendering fixture first used an incompatible checked callback and then an unbound pointer-sized SendMessage argument; both fixture/signature issues were corrected. An early visible preview exposed incorrect draw-message routing: pystray's separate menu owner is not mapped to the icon's message dispatcher. A documented window subclass now routes draw/measure/menu-character messages, and the actual hidden-owner regression passes. No undocumented theme hack was added.
- The first post-rotation documentation check found the moved audit's links; current owners and the archived relative verification link were corrected. Historical test observations remain unchanged.

## Deferred interactive acceptance

An early isolated status-panel view showed dark labels, grouped meters, names, fallback and ellipsis. Later source changes, including list scrolling and final menu-owner routing, have not received complete interactive inspection. Application drawing and pixel checks do not prove native popup borders, post-painted submenu arrows or real navigation.

When the user is ready, run [the synthetic preview](preview_ui.py) through the bounded command helper:

```powershell
& './scripts/run-project-command.ps1' -FileName '.venv/Scripts/python.exe' `
    -Arguments @('Docs/Audits/2026-10-07/preview_ui.py', '--menu', '--many') `
    -TimeoutSeconds 310
```

The preview exits after 300 seconds, uses temporary fixture data, prints control actions instead of invoking real CAC controls, and never connects to Codex or changes login startup. Use `--empty` instead of `--many` for the empty waiting section. In `--menu` mode the status Details button opens the fixture's real native tray popup.

Acceptance must cover final popup/submenus under Windows light and dark themes; hover versus selected versus disabled; Enter/Escape, keyboard/submenu navigation and outside-click dismissal; OK/X/Close; long titles and list-only scrolling; repeated opening and state changes; actual tray icon appearance; taskbar edges, work-area clamping and mixed-monitor DPI. Then run the full native gate and versioned frozen release/update/privacy checks before publication or installation.
