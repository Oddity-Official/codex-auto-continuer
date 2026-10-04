# Verification

CAC 0.5.2, 4 October 2026. Native Windows 11 x86_64, PowerShell 7 and project CPython 3.13.7. Imported checkpoint: v001. [Prior 0.5.1 release evidence](History/2026-10-04-native-0.5.1-validation.md) retains signed-updater, privacy and deployment results for that artifact, not fresh 0.5.2 results.

## Compatibility certification

| Check | Scope | Result |
| --- | --- | --- |
| `scripts/verify-windows.ps1` | Application and workflow regressions, compileall, source version | 240 passed in 57.33 seconds; CAC 0.5.2 |
| `scripts/verify-continuation.ps1` | Official native Codex, separate owners, queued failures, usage-service outage and managed lifecycle | 12 passed in 105.59 seconds |
| `scripts/dev.ps1 -Tests tests/test_supervisor.py` | Focused recovery iteration without packaging | 55 passed in 0.91 seconds |
| Shared policy helper | Safe block replacement and idempotence | 5 passed; all three registered copies current |
| Local Markdown file links | Root and current/historical documentation | 96 checked, zero failures before final documentation update |

The certified CLI and daemon are official Codex 0.160.0, executable SHA-256 `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`, consumer-schema SHA-256 `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`. The native suite explicitly verified the CAC 0.5.2 certificate. Full native settings and scope belong to [continuation tests](CONTINUATION-TESTS.md).

The [dated investigation](Audits/2026-10-04/AUDIT.md) separates the observed quota-read internal error from queued input and causal limits. The new real native regression queues two synthetic follow-ups, observes three quota-failed turns, injects HTTP 503 at the local usage service, preserves pending-state bytes through reconnect, remains blocked while permission is false, then sends exactly one saved Continue after true permission. Existing uncertain-send, malformed-contract and exact-thread regressions remain green.

## Development workflow

Documentation-only CI checks local links without installing/building the application. Portable builds and native probes filter their consumed inputs, retaining manual runs, scheduled upstream checks and full release validation. Exact stable versions resolve before the native matrix; equivalent CLI/daemon tuples run once. Shared policy copies and local `AGENTS.md` preserve completed source handoffs, including prose-only work. Focused timings are not a claim that all delivery checks now finish in one second.

## Release and environment limits

Hosted 0.5.2 publication, frozen-artifact checks and installed replacement results are recorded only after they complete. Existing App monitoring was restored without changing its Continue prompt or logging/client preferences. No conversation-body storage or user-message replay was introduced. The dark menu/status redesign is not part of this recovery patch.

Native computer-control APIs are disabled in this session's tool surface. This is separate from CAC's prohibition on UI automation as a continuation fallback; testing CAC's own UI is allowed. Fresh Windows login, different hardware and a fresh installed VS Code extension pass are not asserted. Experimental queue APIs still lack verified idempotency or an atomic quota/turn/add precondition. EXEs remain unsigned by Authenticode.
