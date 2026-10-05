# Verification

CAC 0.6.0, 5 October 2026. Native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Imported checkpoint: v001. Prior version results below remain dated artifact evidence, not checks of changed code.

## Compatibility certification

The [5 October real-client investigation](Audits/2026-10-05/AUDIT.md) adds isolated installed Desktop and current extension connection proofs, not queue-holding acceptance passes. Actual CLI terminal input exposed a client-local queue, shared-owner provenance caveat and CAC's loaded quota `systemError` deferral. A direct native Continue diagnostic completed, but automatic recovery did not pass. Application code and installed binaries are unchanged; release gates below remain dated unchanged-source evidence.

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
