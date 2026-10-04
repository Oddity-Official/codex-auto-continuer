# Verification

CAC 0.5.2, 4 October 2026. Native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Imported checkpoint: v001. [Prior 0.5.1 release evidence](History/2026-10-04-native-0.5.1-validation.md) retains signed-updater, privacy and deployment results for that artifact, not fresh 0.5.2 results.

## Compatibility certification

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

On 4 October 2026, the [separate queue-control investigation](Audits/2026-10-04-02/AUDIT.md) passed 7 native scenarios in 44.39 seconds against the same official Codex 0.160.0 binary. Two isolated app-server owners, synthetic authentication and a gated loopback inference service exercised client-ID history correlation, owner interruption, unavailable removal methods, selected Continue priority, lost deletion acknowledgement, a before-turn fork and sequential outbox release with usage rechecks. The command deadline was 150 seconds; fixture RPC and gate deadlines were 12 and 15 seconds. Foreign-owner completion waits allow 20 seconds for the ten-second watcher plus execution/persistence.

These are investigation probes, not newly enabled product behavior or a certification of a queue-holding feature. CAC runtime code, release binaries and the installed prompt remain unchanged. No production chat, credential, account allowance or Codex installation was used or modified by the fixtures. The native application gate above is unchanged-source evidence from the release, not a fresh full-suite run for this audit-only change.

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
