# Codex compatibility

CAC defaults to Balanced mode: unknown stable Codex builds may continue after identity, schema and runtime checks pass. Strict mode requires an exact behavior-tested certificate too. Matching schemas are useful evidence, not a behavioral guarantee.

## What is certified

The packaged `src/codex_auto_continuer/compatibility.json` records the CAC version, Windows architecture, full CLI/daemon versions, both executable SHA-256 hashes, recovery and holding contract hashes, suite identity and dated evidence. Current certificates cover official Windows x86_64 Codex 0.160.0/0.160.0, 0.161.0/0.161.0 and mixed 0.160.0/0.161.0 CLI/daemon tuples. [Current verification](VALIDATION.md) owns test results.

This is compatibility evidence, not a security attestation. CAC's own EXEs are unsigned. A user who modifies installed code or its certificate file can modify the application.

## Checks and failure behavior

Every connection checks CLI version, daemon lifecycle identity, initialization user-agent version and the managed binary's version/hash. The product label may contain spaces or change branding; only its structured version participates in matching. Malformed identities and mismatched versions block recovery. The managed binary generates its experimental schema, rather than assuming the invoking CLI describes the daemon. CAC retains prerelease and build suffixes and rechecks identity before resume and queue mutations.

New stable versions and binary hashes trigger verification, not rejection or a required CAC update. Balanced mode accepts them when the consumed contract remains compatible. They appear as Untested because schema evidence is not an exact behavioral certificate. Strict mode deliberately requires the exact tested tuple. CLI and daemon versions may differ; their reported identities must match their respective executables and the connected server.

The supported managed package contains the full `bin/codex.exe`. The separate `codex-app-server.exe` package has no schema generator and is not a supported managed target in Codex 0.160.0. CAC rejects that identity instead of borrowing a same-version CLI schema. CI probes complete CLI packages in the managed role.

The recovery contract covers initialization, thread list/read/turns, account permission/windows, resume and queue add/list/delete. It selects the text input CAC sends, including its empty text-element array, rather than unused media variants or element layouts. Documentation changes, unrelated methods and unconsumed object fields are excluded.

Enum reordering and additional accepted enum values are compatible, except inside exclusive unions where additions can create overlapping branches. Removed values, changed consumed types/constraints, missing fields, changed union branches and new required request fields still block. Actual response guards remain authoritative: an unknown value never becomes permission or a quota failure merely because the schema accepts it.

Full-history client identity, canonical input and queue/turn notifications belong to the holding scope. That scope is checked only when holding is enabled or a held-input journal exists. Normal recovery does not depend on unused holding capabilities. One packaged full baseline supplies both scopes through the same projection, without a duplicate inventory. Existing held data retains the extended checks and remains preserved on a block.

Schemas and binary hashes cache in memory only. Cache keys include full version, binary file identity/hash and capability scope. Generated schema files are removed after inspection. CAC does not contact a certification service, download Codex or change updater settings. Temporary CLI/daemon command failures retry with pending state preserved; malformed protocol data is not treated as a harmless update.

Recovery classifies only the explicit string `usageLimitExceeded`. Its schema projection requires that named variant and its constraints, not every unrelated error variant or diagnostic message. Unknown errors never trigger continuation. This permits forward-compatible error enums without treating a generic string as proof of the quota contract. Other consumed unions and required request fields retain their normal drift checks.

| Evidence | Balanced (default) | Strict |
| --- | --- | --- |
| Exact certificate, identity and schema match | Recovery allowed | Recovery allowed |
| Unknown stable build, identity and schema match | Recovery allowed; untested notice | Queue writes blocked |
| Unknown prerelease, mismatched identity or unverifiable schema | Queue writes blocked | Queue writes blocked |
| Queue contract changed; read contract matches | Read-only discovery | Read-only discovery |
| Read contract changed | Scanning and writes blocked | Scanning and writes blocked |

Set `compatibility_policy = "strict"` in settings, or run `compatibility strict`. `compatibility balanced` restores the default. Runtime quota, exact-thread, ownership and queue-response guards apply in both modes. Neither mode blindly retries an uncertain send.

Status shows the policy, evidence level, CLI/daemon versions and reason. Balanced-mode notices are deduplicated by verified contract and scope, not every binary update. Strict blocks retain build-specific notices. Deduplication persists across restarts; status and telemetry still identify the current builds. Working Balanced mode stays green; a real compatibility block is red. `status --live` includes binary/schema hashes and contract scope. Blocks preserve pending, submitted and uncertain work. The monitor rechecks automatically; repair never requires deleting state. Diagnostic `scan`/`once` return exit code 2 when compatibility blocks recovery.

## Daily upstream probe

`.github/workflows/compatibility.yml` runs on Windows for pull requests, default-branch pushes, manual dispatch and daily at 09:23 UTC. Its independent matrix covers:

| CLI | Managed daemon and separate writer | Purpose |
| --- | --- | --- |
| Certified 0.160.0 | Certified 0.160.0 | Protect the supported baseline |
| Current stable | Current stable | Detect upstream schema or recovery changes |
| Certified 0.160.0 | Current stable | Exercise a daemon updated independently of its invoking CLI |

Jobs create a short `C:/cac-probe` Git worktree before testing. This avoids Codex's 107-byte Windows socket-path limit regardless of the GitHub repository name. Long-path aliases are not used.

GitHub Windows runners are elevated, while Codex correctly rejects elevated daemon startup. CI creates an ephemeral standard account and runs the complete native gate through Task Scheduler, outside the runner's background-process restrictions. It grants access to the disposable checkout and the single batch-logon right, uses an in-memory random password, bounds startup and execution, then removes the task, right and account. The helper refuses normal local execution. Tests and upstream security checks are not skipped or patched.

`scripts/download-probe-codex.py` fetches complete official GitHub release packages into ignored test staging. It requires GitHub's asset SHA-256 and exact size before extraction/execution. Paths, links, duplicates and extracted-size limits are validated. It never installs into a developer's Codex home. Downloads have 180-second deadlines; the outer runner bounds download/extraction at 240 seconds.

The probe resolves exact stable versions and runs each distinct CLI/daemon tuple once, with schema comparison and 18 native scenarios. These use synthetic authentication and loopback model/account services, not an OpenAI login or real allowance. Managed lifecycle tests disable Codex updater/remote control in their disposable home, exercise production discovery/reconnect, deliberately remove certification, prove Strict pending-state preservation and Balanced recovery, then verify one continuation and no duplicates. Owner holding verifies ordered release, quota recovery, encrypted restart, lost replay acknowledgement, coverage and original-client approval routing. Candidate builds receive test-only access inside isolated behavioral fixtures; CI never changes production certificates automatically.

Reports contain versions, checksums, schema differences and synthetic-test results. Jobs fail if either schema or behavior fails. Artifacts expire after 14 days. Compatibility jobs never edit certificates or publish releases; the separate signed release workflow owns publication.

## Certifying another build

1. Run the Windows gate and native continuation gate against the complete candidate package.
2. Run the schema probe and review changes against CAC's actual field usage. For mixed versions, pass `--daemon-executable` to `integration/test_compatibility.py` explicitly.
3. Inspect the behavioral reports. Run the installed extension gate when certifying a new extension-owned writer. Review upstream queue/lifecycle changes even when schemas match.
4. Deliberately update the packaged certificate with exact identities, suite and dated evidence, then rebuild and verify the portable app and wheel. A changed CAC version requires new evidence.

```powershell
& ./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('scripts/probe-compatibility.py','--codex-executable','C:/probe/package/bin/codex.exe','--report','.data/reports/schema.json') -TimeoutSeconds 40
```

`--refresh-contract` regenerates only the consumer contract for a deliberate developer review. It does not certify a build or update certificate hashes. Never use it to silence an unexplained failure.

## What cannot be established

Schema equality cannot prove queue behavior, atomic turn preconditions or idempotent submission. Native tests cannot prove every client/UI or natural service-reset scenario.

The lifecycle response identifies the selected managed binary on disk; the initialization user agent supplies a running version, not an executable digest. Upstream cannot reliably identify a running process after an out-of-band same-version binary replacement. CAC detects changed disk identities, but cannot attest the exact bytes already loaded by every server. Follow upstream's explicit daemon-restart guidance after such replacements. CAC never performs that restart itself. [Upstream daemon lifecycle](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server-daemon/README.md) documents this limit.

A separate CLI, Desktop or extension writer may use another bundled binary. Thread source/originator does not disclose that writer's executable version. Our isolated owner tests provide evidence for the tested builds, not universal mixed-writer certification. The gate certifies the discovered CLI/managed-daemon tuple, and does not pretend to discover an unavailable writer identity.
