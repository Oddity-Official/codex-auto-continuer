# Verification

Native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Imported checkpoint: v001. Prior release results below remain dated artifact evidence, not checks of changed code.

## CAC 0.7.5 status reopening, 8 October 2026

The native close/reopen regression first reproduced a clipped 261-pixel client height against a required 333 pixels. Resetting the cached layout height when creating each new HWND restores full sizing and work-area positioning. All twelve focused status tests passed after repair, including three openings through the same tray controller. The complete Windows gate passed 331 tests in 48.64 seconds, compilation and 0.7.5 identity included.

Computer Use inspected the empty status fixture before and after X dismissal and reopening through the same controller. The new native window retained the correct lower-right work-area position and full 514-by-365 visible frame; both usage meters and reset labels were visible. This is native source-renderer evidence, not a physical mixed-DPI transition or installed binary check. Release and installation acceptance are pending. The existing recovery-engine certificates retain their original verification date because this repair changes only status-window lifetime.

## CAC 0.7.4 release verification, 8 October 2026

Rounded native menus and submenus, clean light arrows, shared dark About/confirmation/error dialogs and the simplified status panel are implemented. Actionable reasons appear directly in Full Status; exact build diagnostics remain in CLI status and local logs. The panel has no Details or Close buttons. Native tooltips expose full authoritative titles without persisting them. Selected tints and right-edge markers remain distinct from hover.

| Check | Scope and result |
| --- | --- |
| Final native Windows gate | 330 passed in 40.60 seconds; compilation and 0.7.4 identity passed, including updater retry/scheduling, native list-wheel and direct fixture cleanup regressions |
| Real native popup regression | Actual Windows tracking with pystray's hidden menu owner verifies rounded region clipping and final light-arrow pixels without a backing box; callback/hook cleanup passed |
| GDI checks | Selected, hover and disabled rows, absent checkmark gutter, arrow/background pixels and remaining-capacity meters at 96/144/192 DPI passed |
| Dialog safety | About OK/X/Escape, confirmation OK/Cancel/X/default Enter/Escape, queue shutdown and recovery from failed window setup passed |
| Interactive source inspection | Computer Use on synthetic, disposable data inspected normal/empty status, nine waiting threads, inline repair guidance, full-title tooltip, rounded main/Clients menus, selected/hover states, native keyboard submenu navigation and About X dismissal |
| Final interactive sweep | Resumed with explicit user authorization: final rounded main/Clients/Telemetry menus, native C/Right/Left navigation, persistent markers versus hover, outside-click dismissal, empty status X, 200% error/unknown-usage layout, bounded waiting-list paging, long-title tooltip, About OK, confirmation default Enter cancellation and error Escape all passed on disposable data |
| Mouse-wheel repair | Interactive inspection caught a waiting list that paged but ignored the wheel without a native scrollbar. Explicit list-only handling accumulates partial wheel steps and clamps at both ends; the regression and actual post-fix wheel inspection passed |
| Local native Codex | Official 0.162.0/0.162.0: all 19 continuation/compatibility/holding cases passed in 111.63 seconds; isolated synthetic services, zero user connections |
| Hosted Windows | [Build and frozen checks](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37881230509) passed on `dc7c849`; the later portable-guide-only commit changes no runtime code |
| Hosted compatibility | [Final matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37881230443): baseline 0.160/0.160, current 0.162/0.162 and mixed 0.160/0.162 each passed 19; native times 143.232, 142.811 and 128.998 seconds, zero failures/errors/skips |
| Signed publication | [Release gate](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37881606243) passed on `ea4c798`, including baseline native behavior, clean builds and frozen checks; private v0.7.4 published |
| Exact downloaded package | Signature, all 607 frozen file hashes, lean package, CRC, configured private markers and frozen UX passed; all 56 wheel runtime files match source, accounting for declared text line endings; development-only psutil is absent from frozen runtime |
| Upgrade and rollback | Real signed isolated 0.7.3 to 0.7.4 completed and rolled back; four protected files and newer state preserved, all 604 original code hashes restored, zero user Codex connections |
| Actual installed upgrade | Completed with restart intent true; monitoring restarted automatically. All 607 installed code sizes/hashes match the authenticated release; actual settings/prompt/state bytes are unchanged |
| Live installed state | Monitoring, CAC/tray 0.7.4, actual CLI 0.160.0 / daemon 0.162.0, Balanced schema-verified read/dispatch permission, ordinary permission true, fresh scan, zero pending/warnings; update state Current |
| Windows login | Owned shortcut still targets the installed GUI/config and normal tray launch; automatic daemon startup is enabled. No interactive CLI window is required. A fresh OS login remains untested |

The first new native popup pixel check caught Windows painting a black arrow after the owner's draw callback. A coalesced popup message now paints the final chevron after that operation. The first dialog regression attempted to read a write-only caption-color DWM attribute; its failed assertion escaped the test callback and the bounded runner stopped the process tree after 90 seconds. The corrected regression catches callback failures, always closes its own window, and checks readable dark/corner attributes. This was a test-harness failure, not an observed product hang. An earlier 322-case gate passed before the explicit setup-failure regression and literal-text fix; the final 323-case gate above covers both.

Physical mixed-DPI transitions, Windows theme switching and high contrast remain untested; no OS settings were changed. The 200% preview controls application scaling, not the physical display setting. Synthetic previews neither connect to Codex nor change real controls. Exact-build certificate metadata retains its original verification date; the new 0.162.0 test evidence does not silently grant Strict certification.

Published 0.7.4 ZIP: 20,399,156 bytes, SHA-256 `e4291fbc37110457bd54beec976d63af83959b591621abf5ace9968c718e24a9`. Wheel: 248,822 bytes, SHA-256 `1d7e436ddbe8fda27dd94b79ccf277cdd8b416473a43ec5370dc6b8f9d947a3a`. The portable README is self-contained and uses a repository URL for update documentation rather than a missing packaged file. No runtime data, developer audits or test dependency is shipped.

### Startup updater diagnosis

The reported update dialog matches the installed Equalizer APO Update Checker: its executable contains the exact title, error text and checkbox wording. No Equalizer APO setting was changed. CAC's separate recorded failure was a five-second GitHub CLI authentication timeout, not a missing Codex executable. Earlier authentication succeeded and a fresh bounded credential read completed in 0.068 seconds; the cause of the temporary delay is not established. Tokens were captured only in memory and never printed.

The source updater retries a timed-out credential read once for ten seconds, distinguishes launch failures from timeouts, and schedules failed automatic checks after fifteen minutes rather than six hours. Focused updater tests passed: 36 cases in 5.42 seconds. Fresh installed 0.7.3 runtime metadata remained Monitoring with CLI 0.160.0 and daemon 0.162.0, Balanced schema-verified dispatch permission, zero pending obligations and zero warnings. This is live compatibility evidence, not exact 0.162.0 behavioral certification or a fresh OS-login test.

### Native test cleanup

Hosted run `37880303865` passed schemas for all tuples and all 19 baseline/mixed cases, but current/current had one teardown failure after successful recovery assertions: PowerShell/CIM process enumeration exceeded ten seconds. The failed result was investigated, not retried away. The fixture now uses development-only `psutil` enumeration and process identities, while retaining same-handle executable verification for termination, actual exit waits and directory-release checks. It does not add `psutil` to CAC's runtime. The real private-versus-external executable cleanup regression rejects shell enumeration and passed with the other cleanup tests in 0.57 seconds.

Local official 0.162.0/0.162.0 then passed all 19 continuation/compatibility/holding cases in 111.63 seconds, including both managed-daemon policies and teardown. Both contract hashes remain unchanged from 0.160.0. These isolated probes use synthetic loopback account/model services and zero user Codex connections; they are behavioral evidence, not an exact-build certificate granted to the user's daemon. The final native gate above covers the cleanup dependency and regression changes too; the preceding 330-case gate took 38.24 seconds before this harness change.

## CAC 0.7.3 startup verification, 7 October 2026

Installed 0.7.2 accepted the actual connected daemon but its automatic start command returned success without a remaining supervisor. Inspection established that status probes briefly acquired exclusive ownership and rewrote PID metadata. Shared read-only probes remove that false-running mechanism; real ownership remains exclusive and survives empty metadata. A short exclusive-acquisition grace period covers in-flight probes, while permission/I/O failures remain explicit.

| Check | Scope and result |
| --- | --- |
| Before-fix regression | A status-only read changed the lock's owner metadata; reproduced failure |
| Native locking regressions | Shared probes do not see one another as owners; start waits for a brief probe; empty metadata and real second-process exclusion remain covered; I/O failure is not a running status |
| Windows gate | 315 passed in 52.66 seconds; compilation and CAC 0.7.3 identity passed |
| Native Codex mixed tuple | All 19 continuation/compatibility/holding cases passed in 117.52 seconds; recovery and holding scopes report Certified with Strict permission |
| Hosted Windows | [Windows build](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37733081821) passed on source `ec48d75`, including frozen checks |
| Hosted compatibility | [Matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37733081806): 19 each, baseline 153.093 seconds, current 151.141 seconds, mixed 136.901 seconds; zero failures/errors/skips |
| Signed publication | [Release gate](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37733474354) passed; exact downloaded ZIP signature and all 604 frozen code hashes/UX checks passed |
| Upgrade and rollback | Real signed 0.7.2 to 0.7.3 completed and rolled back in isolation; all four protected files and newer state survived, all 604 original code hashes restored; zero user Codex connections |
| Real installed upgrade | Completed with restart intent true; monitor restarted automatically, both EXEs/tray report 0.7.3, all 604 code sizes/hashes match, settings/prompt/state bytes unchanged |
| Live installed state | Monitoring, Certified CLI 0.160.0 / daemon 0.161.0, ordinary permission true, all clients, Detailed local telemetry, fresh scan, zero pending obligations/warnings; holding disabled |
| Windows login | Owned shortcut has exact GUI/config target and normal `tray` arguments without a no-monitor flag; fresh OS login remains untested |

The first 314-case gate passed in 52.79 seconds before adding the explicit I/O-error regression. Source architecture records the current lock boundary. This patch changes compatibility and process ownership, not visual design; it does not claim fresh Computer Use acceptance beyond the dated UI evidence below.

Published 0.7.3 ZIP: 20,380,656 bytes, SHA-256 `3c107faab1354f6b2cc054478fab4d3ed3b9b7dfd486fc655b7b93bba361e268`. Wheel: 242,135 bytes, SHA-256 `d3e0bb2e53accb55d32e75892224269a4deb8efdc9ad47489458b2aa565b1af8`; all 53 runtime names/bytes match source and include only 20 current icons. CRC, package boundaries and configured private-marker scans passed. No runtime data is shipped.

Two preliminary upgrade probes expected the old baseline's missing executable to become terminal Failed. The 0.7.2 baseline actually started and retried in Reconnecting, as established by its synthetic telemetry; those probes timed out before upgrade, not because of autostart. A temporary explicit-run setup was removed after identifying the stale phase expectation. The final probe retains tray autostart and accepts either documented unavailable-executable state, then completes upgrade/rollback. This does not alter production recovery or broaden quota classification.

## CAC 0.7.2 compatibility verification, 7 October 2026

The real `Codex Desktop/0.161.0` connection exposed a parser that rejected spaces in product names. The patch validates the version independently of branding and narrows schema checks to the active capability scope. Balanced continues on compatible unknown stable builds; Strict retains exact certification. No Codex installation, update policy or conversation was modified.

| Check | Scope and result |
| --- | --- |
| Before-fix reproductions | Spaced-product and suffix-free product identities failed; additive enum growth independently produced a false schema mismatch |
| Windows gate | 311 passed in 34.91 seconds; compilation and CAC 0.7.2 identity passed |
| Local native tuples | Baseline 18 passed in 117.53 seconds; mixed 18 in 114.01 seconds; current/current final expanded gate 19 in 115.56 seconds |
| Post-certificate scope checks | Real mixed tuple: recovery and holding both report Certified with Strict read/dispatch permission; 2 passed in 4.21 seconds |
| Live production identity | Read-only initialization and schema verification accept the actual 0.161.0 daemon; Balanced read/dispatch permission true, zero mutations |
| Forward-compatibility regressions | Four compatible updates including independent versions and a same-version rebuild; enum addition/order; disabled holding drift; empty text-element layout; malformed/mismatched identity; removed values, constraints, required inputs and overlapping exclusive unions |
| Availability and notices | CLI outage preserves obligation and reconnects; four same-contract binary updates produce one Balanced notice; changed contract and Strict block remain distinct |
| Hosted Windows | [Build and frozen checks](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37730535695) passed on source `fcd040e` |
| Hosted compatibility | [Matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37730535646): 19 cases each, baseline 141.298 seconds, current 161.891 seconds, mixed 203.247 seconds; zero final failures/errors/skips |
| Signed publication | [Release gate](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37731604408) passed, including 311 tests in 39.19 seconds; exact downloaded ZIP signature/checksums and frozen checks passed |
| Upgrade and rollback | Real signed 0.7.1 to 0.7.2, four protected fixture files and newer state preserved, all 604 baseline code hashes restored; zero user Codex connections |

Recovery contract hash: `3e60c81d20a9b640979ba7145bab836198ab2a6cd4a05fc957548ccb82988536`. Full holding hash remains `4f4748360704a777305ba86fbcb0907c8bddab7d5c9063ba032c1899e9f83150`. The [baseline](Audits/2026-10-07/compatibility-072-baseline.json) and [current](Audits/2026-10-07/compatibility-072-current.json) generated reports have no incompatible changes in either scope. Future-version regressions are simulations, not certifications of unreleased Codex versions. Native behavior uses unchanged official binaries and isolated synthetic services; no real model/account requests.

The first hosted mixed job failed during fixture teardown: Windows PowerShell's CIM process enumeration exceeded its ten-second bound. Schema checks passed; the failure was not a recovery assertion. The failed job was rerun on a fresh runner and all 19 cases passed. The original failed attempt remains available in the run history.

Published 0.7.2 ZIP: 20,379,084 bytes, SHA-256 `dbda019dbc18eb4cd229439c59f86ab44f4cd8ce38e2c19e35c2e3ccf00a0fc4`. Wheel: 241,518 bytes, SHA-256 `ffe23778f38fa52a2a39700ddfebfc0a0c455ab1ff3054e6ceff0e579665b4f3`; its 53 runtime files match source and contain only the 20 current icons. Both archives pass CRC, package-boundary and configured private-marker checks. The real installed update completed with restart intent true and compatibility Certified, but monitoring needed a manual start. That observation prompted the separate 0.7.3 ownership repair above rather than a claim of successful automatic monitoring.

## CAC 0.7.1 UI verification, 7 October 2026

CAC 0.7.1 implements the dark native menu, compact status panel, pending-layer icons and transient-status warning repair. Queue holding is absent from the tray; its off-by-default experimental CLI engine and tests remain. The patch fixes UTF-16 title measurement and restores a minimized status window when reopened. Both native regressions failed before repair.

| Check | Exact scope | Result |
| --- | --- | --- |
| Full native Windows gate | `scripts/verify-windows.ps1`; includes visible About close tests, actual hidden menu-owner callbacks, GDI pixels at 96/144/192 DPI, UTF-16 titles, minimized-window restoration, meters, privacy, recovery, encryption, workflow and native cleanup regressions | 293 passed, 35.22 seconds; compilation and 0.7.1 version passed |
| Native Codex integration | All continuation, compatibility and holding modules; isolated official 0.160.0/0.161.0 and mixed tuple, synthetic loopback account/model service | 18 passed for each tuple; exact results in the certification table |
| Hosted compatibility | [Complete matrix](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37687559030), source `4305a36`; reviewed baseline/current/mixed schemas and native behavior | All three tuples passed 18 tests each; zero errors, failures or skips |
| Hosted Windows build | [Windows verification and build](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37687559010), same source | Passed, including the clean-staged wheel builder |
| Source compilation and documentation | Application, tests, scripts and integration compilation; local Markdown targets | Results recorded in the [current audit](Audits/2026-10-07/AUDIT.md) |
| Production telemetry review | Recent cycle/recovery/status metadata only, no public chat names, IDs or bodies | One acknowledged Continue followed by a completed turn; brief tray read failures with no corresponding supervisor stop |
| Actual interactive source inspection | Computer Use on temporary synthetic CAC data, without Codex connections or real control writes | Dark popup and Clients submenu, native keyboard selection/traversal/dismissal, selected versus hover/disabled appearance, normal/empty/long-list panels, full-title Details, error/unknown quota and controlled 200% short-work-area layout inspected |
| Published 0.7.1 frozen package | `scripts/verify-portable.py`; downloaded signed EXEs and isolated control/data paths | All 604 manifest files and UX checks passed; zero Codex connections or user-chat dispatches |

The first manual native invocation passed 14 cases and failed four: a relative executable path failed the absolute managed-binary identity guard, and three fixture cases referenced the obsolete icon filename. The fixture was corrected; the documented wrapper resolves the executable path. The final native result above passed without changing production identity guards.

Interactive testing caught an Enter-key failure missed by the first 283-test gate: `ctypes.wintypes.MSG` uses `hWnd`, not `hwnd`. The corrected key handler has a regression using the actual Windows structure; the final gate above includes it. Details now uses the visible status window as its native owner. Failed source previews and the initial superseded portable check remain in the audit.

The menu interaction fixture uses the production native HMENU renderer, callbacks and Windows tracking loop with a visible test owner. Computer Use cannot reliably target pystray's hidden shell-menu owner. Hidden-owner subclass/lifetime checks run separately in the native suite. Controlled 100/150/200% drawing is not a physical mixed-DPI monitor transition. Windows theme changes, high contrast and mixed-monitor transitions remain hands-on acceptance limits; no Windows privacy/security settings were changed. Native menu borders remain Windows chrome, not custom-painted dark borders.

## Compatibility certification

The final production-status check found that the managed daemon had independently updated to 0.161.0. CAC 0.6.1 blocked its read contract, then a later daemon-start command timeout ended monitoring. The initial 0.7.0 publication run was cancelled before upload. The hosted current/mixed compatibility matrix independently failed for the same projected error union.

Codex changed `CodexErrorInfo` from a closed `oneOf` to an open `anyOf` with unknown string/object variants. The named `usageLimitExceeded` discriminator is unchanged. CAC now projects only that consumed explicit variant; it does not accept a generic-string schema as evidence or recover unknown errors. Both official schemas have consumer hash `4f4748360704a777305ba86fbcb0907c8bddab7d5c9063ba032c1899e9f83150`. Status reports actual compatibility failures as Blocked with their cause, not Not Checked.

| 7 October tuple | Native behavioral gate | Certification |
| --- | --- | --- |
| CLI 0.161.0 / daemon 0.161.0 | 18 passed in 113.76 seconds | Reviewed exact 0.7.1 tuple; schema and connected-build identity checked |
| CLI 0.160.0 / daemon 0.161.0 | 18 passed in 112.43 seconds | Reviewed exact 0.7.1 mixed tuple; same complete native gate |
| CLI 0.160.0 / daemon 0.160.0 | 18 passed in 113.74 seconds | Reviewed exact 0.7.1 baseline |

Fixtures use checksum-verified official packages, isolated Codex homes, unchanged production recovery logic and synthetic loopback services. They make no real model/account requests. The 0.7.1 certificates were added only after these complete behavioral passes. The post-certificate baseline/current connected-build check passed in 2.11 seconds, reporting Certified and Strict read/dispatch permission. Hosted publication and downloaded-package checks are recorded separately.

The [5 October real-client investigation](Audits/History/2026-10-05/AUDIT.md) reproduced and repaired loaded quota `systemError` deferral. Actual CLI composer recovery passed with one completed Continue and three duplicate-free scans. The CLI's queued follow-up remains client-local and unprotected. Normal Desktop composer/history tests accepted two follow-ups exactly once; timed polling did not capture pre-consumption queue IDs. Isolated Desktop and current VS Code composer tests reached Windows setup barriers. None of these results certifies all-client queue holding.

## Published 0.7.1 and installation

The private [0.7.1 release](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.7.1) was built from `dceae31d7065422354d249975fc56e23b72b9242`. The [signed release workflow](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37688154728) passed its Windows, official native, clean build and frozen-package gates before publication. Runtime/build source is unchanged from the complete hosted matrix above.

| Downloaded artifact | Bytes | SHA-256 |
| --- | --- | --- |
| Windows ZIP | 20,376,015 | `835f6f4aa70484ec78cfb3268afbe52d9db0d3e2e4099a80912da94c456d4987` |
| Source wheel | 240,341 | `557470599e2cdf048f4d1fd443347e63dd371b505f04c375aa657ff4948ccaef` |

The downloaded ZIP passed CAC's Ed25519 signature, signed size/hash, CRC and all 604 declared file hashes before execution. Local frozen verification passed defaults, hot reload, invalid settings/prompt repair, exclusive controls, scan feedback, graceful stop, stale-error tray autostart and encrypted review. It made zero Codex connections or user-chat sends. The 61-entry wheel contains exactly 53 current runtime package files and twenty PNG variants; text matches source after checkout line-ending normalization. Both archives passed configured UTF-8/UTF-16 profile/key markers and package boundaries.

The real signed 0.7.0-to-0.7.1 upgrade/rollback probe preserved settings, prompt, state and encrypted held input. It wrote newer state, rolled back code, retained that newer state and restored all 604 baseline code hashes. It used isolated synthetic data and made zero user Codex connections.

The installed App updated through its signed updater. Its durable job completed with running-monitor intent preserved; no manual start was needed. All 604 installed code hashes match the published manifest. Settings, saved `Continue` and durable state are byte-identical. Tray and CLI report 0.7.1. A fresh live scan reports Certified CLI 0.160.0 / daemon 0.161.0, ordinary usage permitted, zero pending obligations and no warnings. All clients and Detailed local logging remain enabled; queue holding remains disabled. The exact owned login shortcut targets the installed GUI/settings with normal tray launch. This is not a fresh operating-system login test.

Current releases and source exports exclude runtime data and configured private markers. The repository remains private. Two historical private commits contain former username canaries from an audit helper, not credentials or conversation bodies. Review or explicitly agree history cleanup before making the repository public; current-file scans do not certify sanitized Git history.

| Published 0.6.1 source check (5 October) | Exact scope | Result |
| --- | --- | --- |
| `scripts/verify-windows.ps1` | Application/workflow regressions, native transport/dialog/menu checks, encryption safety, compileall and version after lock repair | 260 passed in 38.61 seconds; CAC 0.6.1 |
| Actual CLI composer probe | ConPTY input, quota denial, loaded native owner, production CAC discovery and dispatch | Passed; one completed Continue and three duplicate-free scans; zero held client-local inputs |
| Focused lock/holding regressions | Empty PID rewrite under a held Windows lock, process exclusion and private holding safety | 12 passed in 0.86 seconds |
| Repeated native successful-turn holding | 20 independently started processes after the deterministic lock repair; 30-second per-trial and 150-second outer bounds | All 20 passed; encrypted capture, restart, image snapshot and ordered release |
| `scripts/verify-continuation.ps1` | Official native Codex, exact loaded quota recovery, separate-writer recovery, usage outage, managed lifecycle/restart and owner holding | 18 passed in 110.23 seconds; exact 0.6.1 certificate verified |
| Local 0.6.1 `scripts/verify-portable.py` | All 583 packaged files, checksums, lean package, reload/repair, exclusive controls, tray autostart and encrypted review | Passed; zero Codex connections and user-chat dispatches |
| Documentation/privacy boundary | Helper compileall, local Markdown targets, configured profile/identity canaries, Git exclusions and audit retention | 117 links, zero failures; no configured private-profile matches; zero retention deletion targets |

The preceding 0.6.0 source repair passed all 18 native integration tests in 109.22 seconds. The first versioned gate then exposed an intermittent Windows pre-lock write race: 17 passed, one failed in 117.62 seconds. Publication stopped. A deterministic regression failed with the same PermissionError before repair and passed afterward. Diagnostic repetitions established the cause; failed runs remain in the audit. The final native gate above passed. The following release checks are prior 0.6.0 evidence, not a frozen check of 0.6.1.

| Check | Exact scope | Result |
| --- | --- | --- |
| `scripts/verify-windows.ps1` | Application/workflow regressions, native transport/dialog/menu checks, encryption safety, compileall, version | 255 passed in 30.77 seconds; CAC 0.6.0 |
| `scripts/verify-continuation.ps1 -CodexPath .data/ci-official-baseline/package/bin/codex.exe` | Official native Codex, separate-writer recovery, usage outage, managed lifecycle and owner holding | 17 passed in 107.73 seconds |
| Source-export/Git privacy canaries | Portable data, root encrypted journal, settings, logs and environment files | 2 focused tests passed in 3.89 seconds |
| Published `scripts/verify-portable.py` build | Downloaded GitHub EXEs, all 584 manifest files, lean package, hot reload/repair, stale-error tray autostart and encrypted input review | Passed; zero Codex connections and zero user-chat dispatches |
| Publication privacy inventory through implementation | 35 reachable commits, 474 distinct blobs, 159 working files, published ZIP/wheel and refreshed 160-file source handoff | No configured matches, tracked runtime data, private author emails or compiled personal paths; both EXEs and 484 bytecode modules inspected |
| `scripts/verify-update.py --baseline-archive ...0.5.2...zip --private` | Actual signed GitHub 0.5.2-to-0.6.0 upgrade and code-only rollback with synthetic encrypted held input | Completed, then rolled back; all four protected data files and newer state preserved, all 581 baseline code hashes restored; zero user Codex connections |
| Documentation and audit retention | Local Markdown file targets and managed cleanup | 110 links checked, zero failures; zero deletion targets |

The certified official Codex CLI/managed binary is 0.160.0, SHA-256 `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`. The expanded consumer contract is `cb3619a99adfd918d93056553b525dab17b462d4a27a21f5ebbfced3f1bbedf5`, including full-history client IDs, canonical input and queue/turn notifications. The exact 0.6.0 certificate passed the real native gate.

Owner holding tests use production interception/journal/replay code, unmodified Codex and gated loopback model/account responses. They cover successful initial completion, quota denial then unchanged Continue, encrypted engine restart, ordered individual release, lost accepted replay acknowledgement without duplicate execution, foreign-owner warnings and original-client approval routing. A captured image executes after its original local file is deleted, proving canonical embedded snapshot preservation. The actual original client declines the synthetic approval; CAC's observer disconnects without answering.

Focused regressions cover corrupt/mismatched encryption, failed fsync without input deletion, uncertain removal despite absent history, explicit review, manual progress, quota rechecks, no parallel replay, duplicate client identity, disabled/empty journals without Codex connections and blocked-reader abort. The real tray ready callback starts despite historical failed status, avoids duplicate monitoring and honors explicit no-monitor mode. The frozen probe separately exercises a stale-error GUI launch. None of these constitutes a fresh Windows login or universal composer coverage.

An intermediate native run passed recovery assertions but failed managed-daemon cleanup with a Windows socket-directory sharing lock. The fixture previously treated the lifecycle response as sufficient cleanup readiness. It now inventories the isolated daemon's descendants before stopping and waits for actual process exit before directory removal. The affected case then passed; the final full native gate above passed. This repair does not bypass assertions, patch Codex or retry failed recovery behavior.

The first hosted release gate failed before publication: observer cancellation raced the initial socket timeout update, which was outside the transport-error boundary. Deadline updates now normalize closed-socket errors, with a deterministic abort-before-read regression. The focused transport suite passed all six tests; the full local gates above include this correction. The prior candidate's frozen results do not certify the corrected binary.

The next hosted attempt passed the Windows gate but hit GitHub's unauthenticated API rate limit before downloading the native baseline. CI now authenticates only the release-metadata request; binary downloads remain token-free and checksum/size-verified. Both authenticated and unauthenticated download regressions pass, including absence of the synthetic token from output and saved metadata. The final Windows gate includes these helper tests; runtime recovery code is unchanged by this CI repair.

## Published 0.6.1 and installation

The private [0.6.1 release](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.6.1) was built from `7e87281d5d5b2167db9fbada56e9a8cd9dce5439`. Hosted documentation, Windows build, compatibility and [signed release](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37353792572) workflows passed. One duplicate pending publication run was cancelled before it could publish again. The release job passed the standard-user native gate and frozen check before signing.

| Published artifact | Bytes | SHA-256 |
| --- | --- | --- |
| Windows ZIP | 20,229,923 | `2ebd8206603df1203494110532c94e5e53bb0ad7b0d18aadf6a1f9a1ed7520ab` |
| Source wheel | 118,435 | `59603e5b449cc15050c90584d7e558e730436098050027e1f11fc81be561bc1c` |

The exact downloaded GitHub ZIP passed `scripts/verify-portable.py`: all 584 packaged file hashes, lean contents, hot reload/repair, exclusive controls, stale-failure tray autostart and encrypted review. No Codex connection or user-chat dispatch occurred. All 33 wheel package files match local source content; 27 text files differ only by the hosted checkout's CRLF conversion. An initial raw-byte comparison rejected that difference before its cause was verified. Binary assets match byte-for-byte. The ZIP contains no probe dependencies, developer records, runtime data or configured private-profile canaries.

The signed `scripts/verify-update.py --baseline-archive ...0.6.0...zip --private` probe completed the actual GitHub 0.6.0-to-0.6.1 upgrade and code-only rollback. Settings, prompt, state and encrypted held input were preserved. Newer runtime state remained after rollback, all 584 baseline code hashes were restored, and no user Codex connection occurred.

The actual App then upgraded through its existing signed updater. The durable job reached `completed`. CLI, tray and installed manifest report 0.6.1; all 584 installed hashes match the published manifest. Before/after settings, saved Continue and state hashes are identical. Monitoring is active, compatibility is certified and pending count is zero. Holding stays off; All clients, Detailed local logging and automatic authenticated updates retain their settings. The existing login shortcut still points to the exact deployed tray and settings path. This is not a fresh OS-login test.

Real GUI composer tests and their failed observation/setup boundaries are recorded in the current audit. The approved dark UI brief remains unimplemented. No universal queue-holding coverage or natural production quota reset is inferred from the release checks.

## Published 0.6.0 and installation

The private [0.6.0 release](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.6.0) was built from `b90773fba2a28a3244ccbb16b3575f45bbfee460`. Hosted Windows, native compatibility, documentation and [signed release](https://github.com/Oddity-Official/codex-auto-continuer/actions/runs/37278107648) workflows passed. The release workflow includes the frozen UX check before signing/publication. The downloaded artifact passed the local frozen check and real signed upgrade/rollback above.

| Published artifact | Bytes | SHA-256 |
| --- | --- | --- |
| Windows ZIP | 20,230,829 | `6ce0b0d734540f436a4f5e8784da2f3e720e205d035d2f3968dd318730635a27` |
| Source wheel | 118,298 | `3208b4ca551d5521b339c1ffd4d736213b0ebfd58feebf50dc1675a4daaecadb` |

The actual installed App upgraded from 0.5.2 through the signed updater; its durable job reached `completed`. CLI, tray and manifest report 0.6.0. All 584 installed code hashes match the published manifest. Settings, saved prompt and durable state hashes are unchanged. The new monitor reports monitoring, certified compatibility and zero pending work. Queue holding remains off by default; no production input was captured for this verification. The Windows login shortcut still points to the deployed tray and its exact settings path. The startup fix is verified by actual ready-callback and frozen stale-error launch tests, not by a fresh OS login.

No manual mouse/keyboard validation, natural usage-reset experiment or universal installed-client queue capture is claimed. The saved dark tray/status brief is not part of 0.6.0. Scoped cleanup of one old ignored synthetic failed-test directory was rejected by the host; it is excluded from Git, releases and source handoffs. Final native fixtures completed their own cleanup normally.

## Prior 0.5.2 certification

| Check | Scope | Result |
| --- | --- | --- |
| `scripts/verify-windows.ps1` | Application and workflow regressions, compileall, source version | 240 passed in 57.33 seconds; CAC 0.5.2 |
| `scripts/verify-continuation.ps1` | Official native Codex, separate owners, queued failures, usage-service outage and managed lifecycle | 12 passed in 105.59 seconds |
| `scripts/dev.ps1 -Tests tests/test_supervisor.py` | Focused recovery iteration without packaging | 55 passed in 0.91 seconds |
| Shared setup and policy helpers | Safe installation, block replacement and idempotence | 7 passed in 0.31 seconds; all three registered policy copies current |
| Centralized template export | Disposable independently installed helpers | 42 transport/retention tests passed in 33.33 seconds |
| Local Markdown file links | Root and current/historical documentation | 100 checked, zero failures before release-result update |

The certified CLI and daemon are official Codex 0.160.0, executable SHA-256 `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`, consumer-schema SHA-256 `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`. The native suite explicitly verified the CAC 0.5.2 certificate. Full native settings and scope belong to [continuation tests](CONTINUATION-TESTS.md).

The [dated investigation](Audits/History/2026-10-04/AUDIT.md) separates the observed quota-read internal error from queued input and causal limits. The new real native regression queues two synthetic follow-ups, observes three quota-failed turns, injects HTTP 503 at the local usage service, preserves pending-state bytes through reconnect, remains blocked while permission is false, then sends exactly one saved Continue after true permission. Existing uncertain-send, malformed-contract and exact-thread regressions remain green.

## Queue control probes

On 4 October 2026, the [separate queue-control investigation](Audits/History/2026-10-04-02/AUDIT.md) passed 7 native scenarios in 44.39 seconds against the same official Codex 0.160.0 binary. Two isolated app-server owners, synthetic authentication and a gated loopback inference service exercised client-ID history correlation, owner interruption, unavailable removal methods, selected Continue priority, lost deletion acknowledgement, a before-turn fork and sequential outbox release with usage rechecks. The command deadline was 150 seconds; fixture RPC and gate deadlines were 12 and 15 seconds. Foreign-owner completion waits allow 20 seconds for the ten-second watcher plus execution/persistence.

These are investigation probes, not newly enabled product behavior or a certification of a queue-holding feature. CAC runtime code, release binaries and the installed prompt remain unchanged. No production chat, credential, account allowance or Codex installation was used or modified by the fixtures. The native application gate above is unchanged-source evidence from the release, not a fresh full-suite run for this audit-only change.

The [interception follow-up](Audits/History/2026-10-04-03/AUDIT.md) ran 420 measured races: 13 scenarios in 74.09 seconds (120 trials plus offline reconciliation), a 100-trial quota-boundary follow-up in 42.26 seconds, a 100-trial delayed-deletion boundary follow-up in 46.52 seconds and a 100-trial encrypted quota-boundary follow-up in 46.41 seconds. Established owner listeners caught all 50 inputs in each targeted follow-up. Peer polling caught 5/50 at the quota boundary, 2/50 with a 25ms deletion delay and 3/50 with DPAPI encryption before deletion. Accepted peer deletions still resulted in consumption in 20/50, 2/50 and 5/50 respectively. Both idle groups captured 0/10. These are observed fixture counts, not guaranteed interception rates.

Six native/encrypted durability and transport scenarios passed in 10.38 seconds. Fresh subprocesses decrypted synthetic DPAPI journals; deletion/replay acknowledgement loss reconciled without duplicate input; corruption failed; a native image snapshot survived encrypted round-tripping and queue restoration. A stdio owner exposed notifications to its own connection, not to the peer. Neither full conversation persistence nor installed client-composer interception was tested or enabled.

An initial race run passed assertions but had a pytest module-instance reporting bug, so it is excluded from measured results. An initial durability run passed five scenarios and failed on an invalid synthetic PNG checksum. The fixture now uses the repository's valid public icon; all six final assertions passed. Details, deadlines, commands and limits remain in the dated audit. The [UI brief](PRODUCT.md#approved-tray-and-status-refinement) is saved, not implemented; no native UI validation is claimed for it.

## Development workflow

Documentation-only CI checks local links without installing/building the application. Portable builds and native probes filter their consumed inputs, retaining manual runs, scheduled upstream checks and full release validation. Exact stable versions resolve before the native matrix; equivalent CLI/daemon tuples run once. Shared policy copies and local `AGENTS.md` preserve completed source handoffs, including prose-only work. Focused timings are not a claim that all delivery checks now finish in one second.

## Release and environment limits

The private [0.5.2 release](https://github.com/Oddity-Official/codex-auto-continuer/releases/tag/v0.5.2) was built from `08d74f34c673991242fabaede4a6ad6344b4f02a`. Hosted Windows, native compatibility, documentation and signed-release workflows passed. The stable Codex version equals the baseline, so tuple deduplication correctly ran one native tuple, not three differently named copies.

The downloaded GitHub package passed the frozen UX probe: all 581 manifest file hashes, lean contents, spaces/percent paths, implicit defaults, hot reload, invalid-settings/prompt pause and repair, correlated scan feedback, exclusive single-cycle execution and graceful stop. It made zero Codex connections and dispatched zero user chats. This is a functional fixture probe, not manual tray inspection.

The actual installed App upgraded from 0.5.1 through its signed updater. The durable job reached `completed`; all 581 installed file hashes match the release manifest. Settings, saved Continue prompt and durable state hashes were unchanged. The new tray and monitor report 0.5.2, monitoring, certified compatibility and zero pending work. The existing startup shortcut still targets the deployed tray with its settings path. Fresh Windows login was not simulated.

| Published artifact | Bytes | SHA-256 |
| --- | --- | --- |
| Windows ZIP | 20,191,434 | `cff3e30e9d2087f88793837248ce3ead8fb96be2d6fe9da775fdb57d5774f24d` |
| Source wheel | 102,057 | `49e5b0f269e293067b582b16135e043c228a3070b959a49e19ca707717f884bc` |

No conversation-body storage or user-message replay was introduced. The dark menu/status redesign is not part of this recovery patch.

Pre-delivery privacy inspection covered 28 reachable commits, 396 distinct Git blobs, 142 working source files and the downloaded ZIP/wheel plus refreshed source handoff. It found no configured privacy matches, tracked runtime files, private author emails, compiled personal paths or broken Markdown links. Both frozen executables and 481 bytecode modules were inspected. This is a defined inspection, not a guarantee that any conceivable secret pattern is detectable. The repository remains private.

The final result-only push triggered and passed documentation CI without another binary build or native matrix. Changes to workflow code itself retain Windows validation. Source handoffs still refresh for completed documentation deliveries.

Native computer-control APIs are disabled in this session's tool surface. This is separate from CAC's prohibition on UI automation as a continuation fallback; testing CAC's own UI is allowed. Fresh Windows login, different hardware and a fresh installed VS Code extension pass are not asserted. Experimental queue APIs still lack verified idempotency or an atomic quota/turn/add precondition. EXEs remain unsigned by Authenticode.
