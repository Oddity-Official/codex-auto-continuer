# Codex Auto Continuer audit

Audit date: 2026-10-07
Started at: 2026-10-07T11:35:31.757824+00:00

## Scope and boundary

### 8 October status reopening follow-up

Closing Full Status destroys its native window but retains the tray controller's panel object. The old layout-height cache survived that destruction. Reopening with the same content therefore skipped sizing and positioning, leaving the new window at its initial top-left location with a clipped 261-pixel client area instead of the required 333 pixels. A native regression reproduced the failure through `TrayController.show_status()` before repair.

Each new window now resets that window-scoped cache. The regression opens, closes and reopens the same panel three times, checks full content height and monitor work-area containment, and never displays a window or contacts Codex. The disposable preview's `--reopen` option reopens that same panel after X/Escape, for interactive lifecycle inspection. Fresh-object preview evidence alone did not cover this defect. Final verification and release acceptance belong to `Docs/VALIDATION.md`; recovery, prompt, privacy and compatibility policy are unchanged.

### 8 October UI follow-up

The reported square menus, arrow backing boxes, unstyled About window and unnecessary Details/Close status controls are addressed in source 0.7.4. Current behavior is specified in the existing product and architecture owners. This follow-up implements reported UI findings; it does not start a new audit or rewrite earlier evidence below.

Computer Use inspected disposable production-renderer fixtures: rounded main/Clients menus, persistent selected rows versus hover, native C/Right/Left navigation, About X dismissal, nine waiting rows with inline repair guidance, and the full-title tooltip. No Codex connection or real control write was involved. The user stopped Computer Use with physical Escape during the final preview selection. No further desktop input followed; installed 0.7.3 remains unchanged. The final border/button-outline refinements have native tests but not a completed final interactive sweep.

The actual hidden-owner popup regression checks a rounded native window region and final arrow/background pixels under Windows tracking. It initially reproduced a black post-painted native arrow despite correct owner drawing; a coalesced popup message fixes the final paint order. Dialog regressions cover safe confirmation dismissal, About OK/X/Escape, asynchronous shutdown and setup-failure recovery. Final native Windows gate: 323 passed in 31.75 seconds, compilation and 0.7.4 version passed. An initial faulty DWM getter assertion hung its test callback until the 90-second process-tree bound; callback failures now force test-window cleanup and only readable DWM attributes are queried. No production failure was hidden or retried away.

No new portable release, GitHub publication or installed update has been performed for this candidate. The prior 0.7.3 three-tuple integration results are dated unchanged-engine evidence, not new 0.7.4 artifact validation. Complete final interactive and signed/frozen/upgrade gates before release. Current verification is in `Docs/VALIDATION.md`.

### 8 October final acceptance and startup updater follow-up

With renewed explicit authorization, Computer Use completed the final source-renderer sweep. Rounded main/Clients/Telemetry popups, native keyboard traversal, separate selected/hover states, outside-click dismissal, status X, safe confirmation Enter cancellation, About OK and error Escape passed. A controlled 200% application-scale preview verified inline error guidance, unknown usage and bounded waiting-list pagination. The actual normal-scale panel verified untitled fallback, long-title ellipsis and its dark full-title tooltip. No Codex connection, real privacy setting or user control was changed. Existing process-bound preview timers clean up their own fixtures.

The sweep reproduced a wheel-scrolling gap: Previous/Next worked but the scrollbar-free native list ignored wheel input, even with focus. Explicit list-only message handling now accumulates partial steps and clamps movement; a native list regression and actual post-fix wheel input passed. Focused status checks: 11 passed in 3.64 seconds.

The unrelated illegal-value dialog is identified by all three exact screenshot strings in the installed Equalizer APO Update Checker executable and its product metadata. CAC telemetry instead recorded a five-second GitHub CLI credential-read timeout while monitoring continued. No evidence establishes the cold-start delay's cause. A fresh bounded token lookup completed in 0.068 seconds; output was private in-memory capture only. The updater distinguishes missing, launch and login failures, retries only a timed-out credential read once with a ten-second bound, and schedules failed automatic checks after fifteen minutes. Focused updater checks: 36 passed in 5.42 seconds. The final native gate covers all changes: 330 passed in 38.24 seconds, compilation and version 0.7.4 passed. Documentation checks: 138 local file links, zero failures.

Fresh installed 0.7.3 metadata showed Monitoring with CLI 0.160.0 / daemon 0.162.0, Balanced schema-verified read/dispatch permission, zero pending obligations and zero warnings. This does not certify all 0.162.0 behavior or a fresh OS login. No Equalizer APO, Codex installation or conversation was modified. Signed publication, frozen validation and deployment results are recorded separately in the verification owner when completed.

The first hosted 0.7.4 candidate (`e43bc9d`) passed Windows build/frozen checks and baseline/mixed native cases. The current/current 0.162.0 job failed only in teardown after its strict-policy recovery assertions, on a ten-second PowerShell/CIM inventory timeout. Development-only psutil now replaces both shell inventories, retaining live process identity, same-handle private executable verification, actual exit waits and directory sharing checks. The existing real cleanup boundary regression now forbids subprocess enumeration; all three cleanup cases passed in 0.57 seconds. The unchanged official 0.162.0 package then passed all 19 native cases locally in 111.63 seconds. Final Windows gate after this repair: 330 passed in 40.60 seconds. No application compatibility guard was relaxed and no failed recovery result was discarded.

Final source `dc7c849` passed hosted Windows and all three 19-case native tuples. The guide-only `ea4c798` supplies self-contained portable links without changing the tested runtime. Signed publication run `37881606243` passed; exact downloaded v0.7.4 authenticated, matched 607 frozen hashes and all 56 wheel package files, and passed frozen UX/private-marker/package checks. Development-only psutil is absent from the runtime. Actual signed isolated 0.7.3 upgrade and code-only rollback preserved four fixture files and newer state, restoring all 604 baseline hashes, with no user Codex connections.

The installed update completed with restart intent true, all 607 code sizes/hashes match the authenticated package, and actual settings/prompt/state bytes match the pre-install capture. Fresh live metadata is Monitoring with ordinary usage available, CLI 0.160.0 / daemon 0.162.0, Balanced verified-contract permission, no pending obligations or warnings and updates Current. The owned normal login shortcut remains enabled. The first local acceptance wrapper incorrectly tried to collect Write-Host output as pipeline JSON after the successful update launch; its parsing guard failed, not installation. The exact already-returned job was then retained and verified Completed without sending another apply request. Artifact hashes and complete acceptance boundaries belong to Docs/VALIDATION.md.

### Original implementation scope

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

## Final UI pass and 0.7.0 candidate

The user later authorized Computer Use while away. Work continued from source commit `d9db603`, without changing Codex clients or Windows security/privacy settings. The panel now has a prominent state heading, quiet aligned metadata, rounded side-by-side usage cards, borderless waiting rows and compact footer actions. Unchanged snapshots do not repaint; observation and hover tracking stop on close. Short high-DPI work areas reduce list capacity and compact spacing rather than pushing Close off-screen.

Windows post-paints submenu arrows after owner drawing. Drawing our own arrow produced two glyphs. The adapter now leaves the native glyph intact and supplies a light idle backing; the native light hover glyph remains legible on the accent row. Native borders remain Windows chrome.

### Interactive evidence

Computer Use inspected actual native source windows with temporary synthetic state, authoritative fixture titles and 73/41-percent remaining quotas. Control writes print fixture actions; no model, real chat, account request or login change occurs. The visible-owner `--menu` host calls the production popup renderer, callbacks and Windows tracking loop. It exists because the tool could not activate pystray's hidden shell-menu owner reliably; it is not proof of clicking the real shell tray icon.

| Case | Settings and outcome |
| --- | --- |
| Normal and empty status | Three waiting threads; zero waiting threads. Clear hierarchy, authoritative title, Untitled Thread fallback, clean ellipsis; empty section disappears and the window shrinks |
| Bounded long list | `--many`, nine threads. Next scrolls only the list; the header/cards and window height remain stable |
| Compact error/unknown | `--many --dpi 192 --error --unknown`. Controlled 200% application rendering on the existing work area, not a changed Windows DPI setting. Needs Attention, explicit Unavailable/Reset Unknown, one visible row, and accessible footer fit |
| Freshness | Synthetic readings become Last Known after their freshness interval; meters mute rather than imply changing usage |
| Native menu | Settled dark rows, Clients submenu, disabled Start, selected row/right-edge marker, distinct hover, compact meters and no left check gutter. `c`, Right, Left and Escape traverse/dismiss; an earlier native CLI submenu click printed its intended fixture action |
| Full title and keyboard | Selected long title then Enter opens panel-owned Details with the full name and secondary ID/build diagnostics. Enter dismisses the modal; Close dismisses the panel. Escape also closes a source panel |

The first keyboard inspection exposed `MSG.hwnd` instead of the actual `ctypes.wintypes.MSG.hWnd`. It raised AttributeError and ended the panel thread. A regression using the real Windows structure reproduces that boundary. The fixed handler and visible modal ownership passed the later live interaction. The Computer Use helper rejected an owned-modal accessibility index twice; refreshed keyboard activation dismissed it normally. No stale-coordinate retry or substitute UI automation was used.

The first opening snapshot showed native fade transparency; a settled snapshot was opaque. No fade-animation patch was made. Current Windows theme and controlled scale rendering were inspected. Physical mixed-monitor DPI transitions, theme switching, high contrast, other taskbar edges, and direct hidden-shell-owner interaction remain hands-on limits. Computer Use policy prohibits changing security/privacy settings; telemetry options were not changed through automation. No Computer Use screenshot payload was saved in the repository.

### Final local gates

| Gate | Bound and result |
| --- | --- |
| Initial full Windows gate | 283 passed in 43.36 seconds; compilation/version passed. This precedes the Enter repair and does not certify it |
| Final full Windows gate | Normal `scripts/verify-windows.ps1`, 180-second test bound: 284 passed in 45.50 seconds; compilation and CAC 0.7.0 passed |
| Versioned native recovery | Official Codex 0.160.0, unchanged loopback fixtures, 240-second wrapper bound: 18 passed in 112.14 seconds; exact 0.7.0 certificate verified. Later code changes affect only status/dialog presentation |
| Final frozen package | `scripts/verify-portable.py`, 180-second bound: all 603 manifest files and CRC/hash checks passed; implicit defaults, hot reload/repair, exclusive controls, correlated scan, stale-error tray start and encrypted review passed; zero Codex connections/user-chat sends |
| Portable identity | Final local ZIP: 20,302,173 bytes; SHA-256 `4d485587378789155a8eb0a8e2497ed5bbf959c2afe63cbaf4607967c0c387cf`. Earlier candidate ZIPs are superseded, not published |
| Documentation and retention | 128 local Markdown links, zero failures; managed cleanup found zero deletion targets |

Publication, downloaded-artifact verification and deployment results follow separately. The exact hosted package may differ from the local build because hosted Python/dependency versions and checkout line endings differ; its own signed checksum is authoritative.

## Independently updated daemon

The final installed-status read reported CLI 0.160.0 / daemon 0.161.0, blocked `thread/turns/list` and `thread/queue/list`, and no supervisor owner. Local sanitized failure frames show a later daemon-start timeout at 17:23:38 UTC, not a queued-message failure. The daemon is now reachable. The initial private release job [37674083303](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37674083303) was cancelled before publication. The separate current/mixed [compatibility matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37674083568) failed while documentation and Windows packaging passed.

[The schema comparator](compare_contracts.py) identified only `CodexErrorInfo`: closed `oneOf` became open `anyOf` with an additional generic string/object branch. The named string `usageLimitExceeded` remained unchanged. The runtime already rejects every other error; the whole-error projection overreached CAC's actual consumer contract.

The projector now requires the explicit quota enum branch and its constraints. It ignores unrelated errors, not arbitrary request/response union changes. Negative regressions reject missing named discriminators and changed type constraints; existing recovery tests reject unknown and object-shaped quota errors. The baseline was deliberately regenerated with the existing helper; [the baseline report](baseline-schema.json) records that change. [The current report](current-schema.json) has no consumed changes and the same new hash. Reports contain only versions, binary/schema checksums and method names.

The downloaded official 0.161.0 package checksum is `f3093b2483f857ae9085e87e1cc0d22488f65d2374889e4466c23a4f3d374c2d`; its executable matches the locally updated daemon SHA-256 `a0f89acca07a511734cac7fddee26b2106fab68918717bc90df16104a0760a30`. Neither package was installed into the user's Codex home or downgraded.

Native current/current: 18 passed in 113.35 seconds. Native old/current: 18 passed in 109.19 seconds. Both commands used all three integration modules, absolute explicit CLI/daemon paths, 240-second process-tree bounds and isolated loopback fixtures. Exact new/current and mixed certificates were added only after these passes. Status maps schema mismatch, unsupported and unverified contracts to Blocked, prioritizes the specific repair reason, and keeps generic monitor errors in Details.

Post-projection baseline: 18 passed in 111.33 seconds. Separate connected-build checks after certificate insertion report Certified and Strict write permission for current/current (1.61 seconds) and old/current (2.14 seconds). Final full Windows gate: 288 passed in 38.83 seconds; compileall/version passed. Source commit `e40e6b2` contains the correction and three reviewed certificates. Read-only live production inspection reports Certified for the actual old/current tuple and true ordinary permission; it does not restart monitoring or dispatch.

The final corrected local portable ZIP has 603 manifest files, 20,301,801 bytes and SHA-256 `fe7fab627d0c0f95e67938706c8084bde9962841a2da2ee6c3bbce2a0af19f1d`. Its full frozen UX probe passed with zero Codex connections/user-chat sends. [Archive inspection](inspect_delivery.py) passed CRC, every packaged hash, required frozen status code, twenty icon assets, runtime/developer boundary and configured UTF-8/UTF-16 private-profile/key markers. The local 64-entry wheel also passed; it is 258,949 bytes, SHA-256 `14360de18eb530385e07c883544f581f8bd7f62f39fd6fcb296e792e0f374802`. These are local candidate identities, not the later hosted artifacts.

## Hosted teardown and privacy check

The corrected-source [compatibility run 37676226519](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37676226519) passed baseline and mixed tuples. Current/current completed the Strict recovery and duplicate assertions but failed fixture teardown: Windows denied removal of `app-server-daemon/workdir` with error 32. The result was 17 passed, one failed in 202.55 seconds. Publication remained stopped. The accompanying Windows and documentation jobs passed.

Fixture cleanup already waited for recorded processes to exit. It now also opens the exact working directory with DELETE access and full sharing before removal. This tests Windows delete-sharing readiness without deleting anything. Only sharing violations receive a bounded wait; other errors fail immediately, and an unreleased directory fails clearly after 5 seconds. Cleanup does not ignore removal errors or rerun behavioral assertions. A native regression holds a directory handle without delete sharing, requires the readiness check to fail, closes the handle, and requires success with the directory still intact.

Archive privacy canaries are now repeatable local `--private-marker` arguments, not personal identifiers embedded in the audit helper. The current source and release can be checked without putting those identifiers into exported source. Two private, already-pushed commits contain the former helper's username canaries. They contain no credentials or conversation bodies, but current-file scans do not establish sanitized Git history. The repository must remain private unless those historical canaries are reviewed or removed through an explicitly agreed history-cleanup operation.

The repaired native directory-sharing regression passed in 0.21 seconds. The final Windows gate passed 289 tests in 47.26 seconds, including compilation and CAC 0.7.0 identity. The full current/current native suite passed 18 tests in 113.15 seconds after the fixture change. Documentation checked 132 local links with no failures; current audit helpers compiled, and retention found no deletion targets.

An additional final source preview was inspected through Computer Use: clear state heading, quiet metadata, rounded side-by-side usage cards, bounded waiting list, long-title ellipsis and distinct selected-row styling. The visible Close button dismissed the panel. The exact disposable preview process chain was identified and stopped afterward; no installed CAC or Codex process was stopped.

The next [hosted matrix 37679483217](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37679483217) passed baseline and current/current. Mixed old/current completed the Strict behavioral assertions but failed deleting its private copied `codex.exe`: 17 passed, one failed in 178.54 seconds. The directory-sharing check did not establish executable release. No release was published.

Teardown now also inventories detached processes whose executable is inside that exact fixture home after the supported lifecycle stop. Each candidate is opened once with query, terminate and synchronization rights. Its executable is revalidated through that retained handle before termination and a bounded exit wait. A PID recycled to an external executable fails without stopping it. The inventory does not select by process name, global Codex home or user chats. The fixture records only a count of any reaped private-package processes. A native regression launches a private copied executable and an external executable with the same name; cleanup stops only the private copy. Both native cleanup regressions passed in 3.39 seconds.

After that repair, the final local Windows gate passed 290 tests in 47.08 seconds; compilation and 0.7.0 identity passed. All 18 mixed old/current native scenarios passed in 111.44 seconds. The existing signed 0.6.1 baseline was verified against CAC's Ed25519 trust record, CRC and all 584 packaged file hashes before any upgrade probe executes it.

The [following hosted matrix 37681078755](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37681078755) passed baseline and mixed, but current/current again failed Strict fixture cleanup (17 passed, one failed in 232.42 seconds). No release was published. The fixtures used one ExitStack for both process shutdown and TemporaryDirectory removal; a later removal exception could replace the actual shutdown failure. The temporary home is now explicitly removed only after all shutdown callbacks succeed, with its resolved parent and link boundary checked. On shutdown failure it remains isolated and the primary error reaches pytest. A regression verifies this failure-preservation behavior. The fixture prints only shutdown counts and return codes, not credentials, commands or chat contents. Three cleanup regressions passed in 3.68 seconds.

## Signed 0.7.0 delivery

Source `b2c8425` passed the [complete hosted compatibility matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37682413159): baseline 18 tests in 158.541 seconds, current/current 18 in 152.273 seconds, and mixed 18 in 134.792 seconds. Each report has zero errors, failures or skips. The [Windows build](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37682413086) also passed. Earlier teardown failures remain recorded; this successful run does not establish their precise underlying cause. Cleanup now checks exact private identities and preserves primary shutdown failures.

The final local native gate passed 291 tests in 35.37 seconds, compilation and version. The private [signed release workflow](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37683248428) passed and published [CAC 0.7.0](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.7.0) from that source.

The downloaded ZIP's Ed25519 signature, signed size/hash, CRC and all 604 manifest files passed before execution. ZIP: 20,376,034 bytes, SHA-256 `6ba1aa327f5a86d7f51919f6e85d03007584195c68e636f3de7fc7f092fd98b1`. Frozen UX verification passed all reload, repair, exclusion, startup and encrypted-review checks with zero Codex connections/user-chat sends. The published wheel has 61 entries, 240,336 bytes, SHA-256 `4a02022fe884252ca2016af80e0f4553fb92569d5fb72e8789750f4613adb1f2`; its twenty PNGs and runtime Python source match current source. Both archives passed configured UTF-8/UTF-16 profile/key-marker and package-boundary inspection.

The signed upgrade/rollback probe used the actual published 0.6.1 baseline, not a fabricated version. It upgraded to 0.7.0, preserved settings/prompt/state/encrypted input, wrote newer state, rolled code back, preserved newer state and restored all 584 old code hashes. It made zero real Codex connections.

The actual portable install then updated through the existing signed updater. All 604 declared code file sizes/hashes matched. Settings, prompt and state were byte-identical before monitoring was restarted. The first installed-file check incorrectly used the staged-bundle verifier; it rejected the installed data folder as designed. The corrected installed check compares the declared code files while leaving runtime data outside that file set.

The tray reports 0.7.0; monitoring was explicitly started. A live read reports Certified CLI 0.160.0 / daemon 0.161.0, true ordinary usage permission, a fresh scan, no warnings and zero pending obligations. All three clients, Detailed local logging and the saved `Continue` prompt remain selected; holding remains disabled. The owned login shortcut still targets the installed portable GUI with the exact settings file and normal tray launch, without a no-monitor flag. A fresh operating-system login was not performed.

## Final UI edge regressions and clean wheels

Final native API checks exposed two additional presentation defects. An emoji-bearing title measured 103 pixels instead of the native full-string 109 pixels because Python code-point length was passed as a Windows UTF-16 length. The renderer now uses the API's null-terminated length. A minimized native fixture remained minimized after the reopen callback; that callback now restores the window. Both regressions failed before repair and all ten status tests passed afterward in 3.81 seconds. The minimized fixture is offscreen and non-activating; it does not manipulate user applications.

These runtime changes require patch release 0.7.1, not replacement of the already-published 0.7.0 package. All 18 native scenarios passed for 0.7.1 baseline (113.74 seconds), current/current (113.76 seconds) and mixed (112.43 seconds), before adding the reviewed 0.7.1 certificates. Existing 0.7.0 certificates correctly did not certify the new CAC version. The consumer contract and official binary identities remain unchanged. Local editable metadata was refreshed to match source 0.7.1; it had still described an older release, though the hosted builds were fresh.

The old checkout-local Setuptools cache contained three removed icons, explaining the superseded 64-entry local wheel versus the clean 61-entry hosted wheel. The [wheel builder](../../../scripts/build-wheel.py) now stages current source and declared license inputs, uses the normal backend, checks exact package names and bytes, and atomically replaces output only after validation. It does not delete or depend on the old cache. Two actual source builds completed in about 4 seconds with all 53 runtime package files matching; the stale three icons were absent. CI and contributor instructions use the same builder. This does not require republishing the unchanged 0.7.0 binary for documentation/build-helper edits.

Final 0.7.1 Windows gate: 293 passed in 35.22 seconds; compilation/version passed. After certificate insertion, the actual baseline/current connected-build check passed in 2.11 seconds, reporting Certified and Strict read/dispatch permission. A fresh clean-staged 0.7.1 wheel verified all 53 package files. Documentation checked 133 local targets with zero failures. Whitespace checks passed with native CRLF handling.

Computer Use inspected the final 0.7.1 synthetic panel: an emoji-bearing authoritative title, complete readable state/metadata, rounded usage cards, neutral untitled fallback, clean long-title ellipsis and footer actions. The visible Close button dismissed it. The exact disposable preview chain was inspected and stopped; the installed monitor was not stopped. No screenshot payload or private production title was persisted. The native minimized-window regression establishes restore behavior without relying on the automation tool's own activation.

Source `4305a36` passed the [hosted Windows build](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37687559010) and [complete compatibility matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37687559030). Downloaded JUnit reports show 18 tests per tuple: baseline 151.260 seconds, current/current 151.864 seconds and mixed 133.445 seconds. Each has zero errors, failures or skips. The subsequent documentation-only commit `dceae31` changes no runtime, tests, compatibility or build helpers.

## Signed 0.7.1 delivery

The private [signed release workflow](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37688154728) passed in 6 minutes 15 seconds and published [0.7.1](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.7.1) from `dceae31`. Its release-specific native gate, clean portable/wheel build and frozen verification passed before signing.

The exact download passed Ed25519 authenticity, signed size/hash, CRC and all 604 file hashes before execution. ZIP: 20,376,015 bytes, SHA-256 `835f6f4aa70484ec78cfb3268afbe52d9db0d3e2e4099a80912da94c456d4987`. Wheel: 240,341 bytes, SHA-256 `557470599e2cdf048f4d1fd443347e63dd371b505f04c375aa657ff4948ccaef`. Both passed configured UTF-8/UTF-16 profile/key-marker and package-boundary checks. All 53 wheel runtime files match source, with twenty PNGs and no stale icons; text normalization accounts only for checkout line endings.

Local exact-download frozen UX passed all 604 hashes, defaults, reload, settings/prompt pause and repair, correlated scan, exclusive control, stop, stale-error tray autostart and encrypted review. The real signed 0.7.0 baseline upgrade reached completed, then rolled back. All four protected data files and newer runtime state survived; all 604 baseline code hashes restored. Both probes used synthetic isolated homes and zero user Codex connections.

The real App update completed with `restart_monitor = true`; monitoring restarted automatically. All 604 installed code sizes/hashes match. Pre/post settings, saved Continue and durable-state bytes match. Tray/CLI report 0.7.1. A live scan reports monitoring, Certified baseline CLI/current daemon, true ordinary permission, all clients, Detailed local logging, zero pending obligations and no warnings. Holding stays off. The owned shortcut's exact target/arguments and absence of a no-monitor flag passed; fresh OS login remains untested.

Two read-only inspection commands initially assumed stale helper shapes: the tray's post-restart update status no longer contained a job path, and the shortcut helper returns a dictionary rather than a COM object. The corrected checks use the exact launch result's durable job path and documented dictionary keys. No updater/startup failure, user-data mutation or second installation occurred.

## 0.7.2 identity and forward compatibility

Base source: `c3c75dc`, Windows 11 x86_64, PowerShell 7, CPython 3.13.7. The actual running daemon reports `Codex Desktop/0.161.0`; the old user-agent parser allowed no space before the version separator. It rejected the connection despite matching machine-reported CLI/daemon/binary versions. No missing binary or usage failure was established. Loading the installed tray alone did not remove this compatibility block.

Permanent reproductions failed before repair: spaced and suffix-free product labels were rejected (three failed cases and one valid-label control passed). A separately rerun additive-enum case used the old valid label and failed with `schema_mismatch`, establishing an independent false block. Product labels and platform suffixes are now display text; full version matching remains mandatory. Invalid/control-bearing identities and mismatched versions are negative regressions.

The comparator accepts enum ordering and safe additions while preserving required fields, types, constraints and union branches. Exclusive unions do not allow enum growth that could introduce overlapping branches. Normal recovery projects only its text request, empty text-element array and metadata replies. Holding's full inputs/history/notifications are checked when enabled or a journal exists. The two scopes derive from one stored full baseline; no duplicate schema inventory or temporary-format migration path remains.

Recovery digest is `3e60c81d20a9b640979ba7145bab836198ab2a6cd4a05fc957548ccb82988536`; full holding remains `4f4748360704a777305ba86fbcb0907c8bddab7d5c9063ba032c1899e9f83150`. Sanitized [baseline](compatibility-072-baseline.json) and [current](compatibility-072-current.json) reports contain versions, binary/contract hashes and method names, not user-agent platform/account data. Both scopes match official 0.160.0 and 0.161.0 schemas.

Binary/version changes still invalidate evidence and cache keys. Balanced permits compatible stable builds without an allowlist update; Strict requires exact certification. Four simulated compatible updates, including independent CLI/daemon versions and same-version replacement, remain Untested and permitted only in Balanced. A new required input, removed enum, changed constraint or ambiguous exclusive-union growth remains blocked. These simulations do not certify hypothetical native releases.

Temporary CLI/daemon command failures now use bounded reconnect behavior instead of terminating monitoring. A regression preserves an existing obligation and forbids writes through an outage. In-memory identity/schema checks still repeat before mutations; quota, exact-thread, approvals and ambiguous-send guards are unchanged. Balanced notices deduplicate by contract/scope rather than binary tuple, while status/telemetry retain build identities and Strict blocks retain distinct notices.

Focused recovery/compatibility/update tests passed 132 cases with only the deliberately stale certificate assertion deselected before certificate refresh. Preliminary native baseline/current/mixed suites each passed 18 cases. After baseline deduplication, final local baseline passed 18 in 117.53 seconds, mixed 18 in 114.01 seconds and current/current 18 in 117.09 seconds. The post-certificate mixed native scope check passed both scopes in 4.21 seconds. A new permanent scope parameter expands the native suite to 19 cases. After the exclusive-union guard, final current/current passed all 19 in 115.56 seconds. All commands had 240-second outer process-tree bounds and isolated homes/services.

Final Windows gate: 311 passed in 34.91 seconds, compilation and 0.7.2 version passed. An earlier 311-case gate passed in 38.35 seconds before the exclusive-union tightening. A read-only source probe accepted the actual running daemon in Balanced mode before certification insertion, reporting Untested, matching version 0.161.0 and allowed recovery scope; it performed no thread reads, queue mutations or model calls. The installed 0.7.1 app remained blocked during source verification; no unsigned hot patch or daemon restart was used. Signed package and installation evidence follows separately.

Source `fcd040e` passed hosted Windows/build/frozen checks and final baseline/current/mixed compatibility reports, each with 19 cases. First mixed attempt failed in fixture teardown: Windows PowerShell CIM enumeration timed out at ten seconds, not a recovery assertion; the fresh-runner retry passed. Signed publication run `37731604408` passed. The exact downloaded 0.7.2 ZIP authenticated and passed all 604 frozen hashes/UX/privacy checks; its wheel's 53 current runtime files match source. The real signed 0.7.1 fixture upgrade and code-only rollback preserved four protected files and newer state, restoring all 604 baseline code hashes with zero user Codex connections.

The real installed 0.7.2 update completed with `restart_monitor = true`. Its connected identity/schema check reported Certified for the actual CLI 0.160.0 / daemon 0.161.0. However, the tray's start command reported exit zero and no supervisor remained. A manual normal start succeeded, making this an installed-startup observation rather than a failed compatibility repair. No settings or prompt were changed. The initial preservation helper incorrectly treated the configured relative prompt string as a resolved Path; the corrected helper uses `prompt_path`. A later assertion assumed the saved Continue had no final newline; content equality must not imply byte normalization.

## 0.7.3 shared ownership probes

Base source `fcd040e`. Existing `is_running` acquired the same exclusive lock used by real owners and rewrote its PID. Concurrent observers could see one another as owners, so a normal start could return already-running based on the stale owner record. The metadata-preservation regression failed before repair (a status read replaced the fixture's PID). This establishes the mechanism consistent with the installed autostart observation; no captured Start stdout proves which precise probe won that race.

Status now uses shared, read-only native range locks, including beyond EOF. Real ownership remains exclusive. An exclusive acquisition allows 100 milliseconds for short probes to finish; real duplicate owners are still rejected. Permission/I/O failures are distinguished from lock contention. Tests cover concurrent probes, preserved metadata, delayed start behind a probe, an empty file under ownership, actual second-process exclusion and error propagation. No lock metadata is treated as ownership authority.

Preliminary 314-case Windows gate passed in 52.79 seconds. Final gate with I/O regression: 315 passed in 52.66 seconds, compilation and 0.7.3 identity passed. Native official mixed tuple passed all 19 cases in 117.52 seconds, with both recovery and holding Certified under Strict. Commands were bounded and used isolated synthetic homes/services, with no real model/account requests. The already-published 0.7.2 was not overwritten; 0.7.3 owns the extra startup repair. Publication and installation are verified separately below.

Source `ec48d75` passed hosted Windows/build/frozen checks, all three 19-case compatibility tuples and signed publication run `37733474354`. Final hosted native times: baseline 153.093 seconds, current 151.141 seconds, mixed 136.901 seconds, with zero failures/errors/skips. The exact downloaded signed 0.7.3 ZIP authenticated and passed 604 hashes, frozen UX, CRC, package boundaries and configured private markers. Its 53-file runtime wheel matches current source. Artifact hashes and byte counts belong to the verification owner.

Two preliminary 0.7.2-baseline update probes timed out waiting for Failed before any upgrade. Fixture telemetry established that the baseline did start and kept retrying its deliberately absent executable as Reconnecting. An initial diagnosis attributing this fixture failure to autostart was corrected. The temporary direct-run setup was removed; the final probe retains normal tray autostart and accepts Failed or Reconnecting as the documented missing-executable state. Final signed 0.7.2 to 0.7.3 upgrade/code-only rollback passed, preserving four protected fixture files and newer state, restoring all 604 baseline code hashes, with zero user Codex connections.

The actual App upgrade completed with restart intent true. Monitoring restarted without a manual start, and the fresh scan reached Monitoring/Certified for actual CLI 0.160.0 and daemon 0.161.0. Both read and dispatch checks and ordinary permission are true; all clients, Detailed local logging, holding disabled, zero pending work and no warnings. All 604 installed code sizes/hashes match; settings, saved Continue (including its newline) and state hashes match both the pre-0.7.2 and pre-0.7.3 captures. Tray PID/path/version and exact owned normal login shortcut passed. No Codex restart, update setting or conversation mutation was used to repair compatibility. Fresh OS login and original unexplained tray absence are not established by this installed update check.
