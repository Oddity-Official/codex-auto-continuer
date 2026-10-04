# Natural recovery observed on 4 October 2026

CAC 0.3.0 recovered this development Desktop chat without a human continuation. The evidence is retained in local metadata logs and the session event stream, not uploaded source fixtures.

| Event | Time (PDT) |
| --- | --- |
| Structured usage-limit turn completed | 02:31:13 |
| Exact obligation detected | 02:31:47 |
| Ordinary usage confirmed and one queue submission acknowledged | 03:02:36 |
| Saved Continue appeared and the subsequent turn started | 03:02:40 |
| Session completion event, no error | 04:04:55 |

The retained telemetry contains exactly one acknowledged submission for that chat in this interval. Matching exact IDs and timestamps link the obligation, queue entry and subsequent turn. No prompt bodies, real IDs, private paths or chat names are included in this public record.

At 03:03:10, the shared server reported the subsequent turn as interrupted/notLoaded with no completion timestamp. CAC ended observation too early. Session events show the original writer kept working until 04:04:55. CAC 0.5.0 retains observations until terminal completion evidence exists; regressions cover separate-owner incomplete history and restart.

This demonstrates natural recovery for one Desktop chat and the installed 0.3.0 policy. Subsequent-turn metadata alone does not prove causation in the presence of concurrent user input. Controlled native tests cover exact targeting, denied quota, separate ownership, ambiguous acknowledgements and duplicate prevention independently.
