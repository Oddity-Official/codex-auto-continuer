# Verification

Current checks completed on 4 October 2026. Application: 0.3.0. Reviewed baseline: `f8abd3c`; imported checkpoint: v001, verified bootstrap `643ba04`. Publication work changes documentation, workflow and tests, not application behavior. [Historical records](README.md#historical-records) retain earlier release, activation and telemetry measurements.

## Environment

| Item | Exact value |
| --- | --- |
| Native host | Windows 11 build 10.0.26300, x86_64; PowerShell 7.6.6 |
| Python | CPython 3.13.7; isolated virtual environments |
| Runtime dependencies | pystray 0.19.5; Pillow 12.3.0; TOMLKit 0.15.1; six 1.17.0 |
| Test/build dependencies | pytest 9.1.1; PyInstaller 6.22.3; hooks 2026.8; setuptools 84.0.0; resvg-py 0.5.0 |
| Native Codex baseline | CLI and daemon 0.160.0 |
| Frozen-probe settings | No clients selected; poll 1s; isolated control directory; no Codex connections |
| Normal release defaults | All three interactive clients; 24h discovery; poll 30s; prompt Continue; Private logging; trace off; 8 MiB/three gzip backups |

## Native and clean-source checks

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-03-03/probe_clean_source.py') -TimeoutSeconds 600
```

| Check | Observed result |
| --- | --- |
| Final native gate | 163 passed, no skips or warnings, 43.79s; compileall including integration sources and version 0.3.0 passed; prior explicit interpreter selection exercised |
| Fresh source export | 96 files copied through transport exclusions; no parent checkout, deployed app, data, Git metadata or pre-existing venv required |
| Fresh dependency installation | `.[dev,build]` installed in a new venv without a second global installation |
| Fresh native gate | 163 passed, no skips or warnings, 54.69s; compileall and version passed |
| Fresh portable and wheel builds | Both passed; portable ZIP CRC and all 521 manifest file hashes verified |
| Fresh frozen integration | Default settings/prompt, exclusive once, scan feedback, same-PID reload, invalid-settings/prompt pause and repair, graceful stop; zero Codex connections or user-chat dispatches |
| Current artifacts and docs | Deployed 521 file hashes, wheel module/asset parity and repository Markdown file targets passed |

The gate selects the local venv, or the configured launcher if no venv exists; `-PythonPath` is explicit. Version/import checks are bounded at 30s, pytest at 180s and compileall at 120s. The clean-source probe bounds environment creation at 60s, installation at 180s, gate at 300s, builder at 360s, wheel at 120s and frozen integration at 150s; each timeout stops its owned process tree.

Native socket tests initially failed under the venv when their listeners were created in this host's system temp directory, with Winsock 10022 and cleanup error 1920. Canonicalizing the path did not fix it. Short checkout-local socket fixtures pass under both global and venv interpreters; a venv connection to the real daemon also passes. The production transport was not changed. The exact host/Windows cause is not established.

The suite covers quota authority, exact targeting, durable obligations, manual-progress cancellation, ownership, ambiguous sends, protocol deadlines, native sockets and locks, settings/prompt safety, native About closure, popup highlights, startup ownership, telemetry privacy/rotation and destructive-path/transport boundaries. Two new regressions verify Git exclusions and source-export privacy with synthetic canaries, including environment-file variants and non-default backup counts.

## Native continuation chain

```powershell
pwsh -NoProfile -File scripts/verify-continuation.ps1
```

The standalone gate runs eight scenarios against installed, unmodified Codex 0.160.0, with two native app-server owners per case. [Native continuation tests](CONTINUATION-TESTS.md) owns the exact settings, service shapes, isolation, deadlines and assertions. No real account credentials, chat home or allowance are used. The existing installed tray/supervisor processes and saved prompt remain unchanged.

Final result: 8 passed, no skips or warnings, in 60.77s, including compact Private telemetry checks. The earlier full native run also passed. The 163-test Windows gate is separate; native integration is not silently skipped by the normal gate or required by GitHub CI.

| Scenario | Verified result |
| --- | --- |
| Quota-to-continuation chain | Native HTTP 429 persisted failed/usageLimitExceeded and numeric completedAt. Three denied scans after an advisory reset sent nothing. State reload retained the obligation. Verified allowance led CAC to send exactly one saved Continue through the original owner's native queue, completing the next turn of the exact chat. |
| Unrelated chat and subsequent reload | Another successful chat stayed untouched. Reload and three further cycles created no duplicate turn or remaining queue item. |
| Account and user mismatches | Both cases yielded native null permission despite backend allowance; no send. |
| Manual progress | A native manual turn before recovery cancelled pending work; later allowance and reload did not continue it again. |
| Invalid and repaired prompt | Empty prompt blocked before submission and preserved pending state. Repair sent newly saved text rather than a cached/default value. |
| Two quota failures | Native failures were recorded independently. Permission denial after the first dispatch stopped the second; later verified permission resumed it exactly once. |
| Lost queue response | Native acceptance and completion occurred despite discarded acknowledgement. CAC saved uncertainty; reload did not resend. |
| Queue write not accepted | No native queue entry or advanced turn existed. Repeated reconciliation failed explicitly after its deadline without retrying the send. |
| Local telemetry | Detection, permission transition, separate-owner handling, intent, one submission and observed completion were retained. Private logs excluded real fixture IDs, synthetic credentials and chat bodies. |

This proves the controlled native recovery chain. It does not turn a service fixture into evidence of a real quota reset. The harness selects isolated sockets directly and reloads engine/state objects; it does not exercise production daemon discovery, actual UI clients, tray process restarts or Windows login.

## Publication privacy

```powershell
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('Docs/Audits/2026-10-03-03/probe_publication.py') -TimeoutSeconds 120
```

The initial scan checked all five existing commits and 171 unique Git blobs. No credential-shaped values, real local profile/project paths, runtime data or private author emails were found. Authors use a GitHub no-reply address. The changed working tree is scanned separately before delivery.

The continuation-test follow-up scan checked six existing commits, 192 unique blobs and all 101 source files. It found no privacy matches, tracked runtime files, private author emails or broken Markdown file targets. The unchanged portable ZIP and refreshed wheel also passed deep inspection. Source transport is rebuilt and checked again after the scoped commit.

The portable ZIP has 522 entries: 521 release files plus its manifest. Inspection covers both executable CArchives/PYZ archives, nested `base_library.zip`, 440 Python bytecode modules and embedded code filenames, not just compressed file bytes. No local profile/project paths or credential matches were found. The 30-entry wheel is also clean. These checks combine targeted scanning with manual review; they are not proof that an arbitrary secret can always be recognized.

One public Git repository retains sanitized audits and manifests. No history rewrite or GitHub upload was performed. Runtime folders, root runtime files, environment-file variants and log backups are excluded from Git and source export through separate rules. Custom data locations still require explicit exclusions.

The Windows workflow uses read-only permissions and commit-pinned official actions, without persisted checkout credentials. Its equivalent commands passed locally; GitHub-hosted execution remains unobserved until the repository is uploaded.

## Release artifacts

The unchanged portable ZIP is `dist/codex-auto-continuer-0.3.0-windows-x86_64.zip`, 16,299,281 bytes. SHA-256: `f3377108c1435400b6c6d723eb84f96e14245d12846dc1a6125b10a1ab5ed545`.

The wheel is `dist/codex_auto_continuer-0.3.0-py3-none-any.whl`, 72,678 bytes, with updated README metadata. SHA-256: `911271df4f6539cbb3770ed115e1e2f82ffe25c3f2b0bd29c3bf07f4d7c8028c`.

The stable full-source handoff is `codex-auto-continuer-codex-handoff.zip`; its manifest records source hashes and Git provenance. It includes development records, unlike the lean portable app. Builds are not claimed to be byte-for-byte reproducible.

## Remaining limits

- Actual VS Code extension UI delivery and a natural account-reset automatic continuation have not been observed. Shared-protocol support is an inference where direct evidence is unavailable.
- Two simultaneous real quota failures were not available; multi-chat safety is covered by regression fixtures.
- Shortcut launch is verified, not a fresh Windows login.
- Native dialog/button checks are not a manual mouse or screen-reader review. Associated-editor launch is tested, not external editor startup performance.
- Queue addition has no verified atomic turn precondition or idempotency contract. Immediate revalidation cannot eliminate every concurrent-progress race.
- Subsequent-turn telemetry reports observed metadata, not guaranteed attribution to a queued message.
- Other Windows/Codex installations must pass capability checks. EXEs are unsigned; SmartScreen reputation and other machines have not been tested.
- GitHub-hosted CI has not run. Five failed system-temp socket fixtures remain outside the repository because the host rejected their cleanup; no such fixtures are in source or release artifacts.
