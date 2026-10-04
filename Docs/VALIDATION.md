# Verification

Current checks: 4 October 2026. Application: CAC 0.4.0. Implementation baseline: `6016c21`; imported checkpoint: v001. [The dated 0.3.0 record](History/2026-10-04-native-0.3.0-validation.md) preserves earlier publication, extension and icon evidence.

## Environment

| Item | Exact value |
| --- | --- |
| Host | Windows 11 build 10.0.26300, x86_64; PowerShell 7.6.6 |
| Python | CPython 3.13.7, project `.venv` |
| Runtime | pystray 0.19.5; Pillow 12.3.0; TOMLKit 0.15.1; six 1.17.0 |
| Tests/build | pytest 9.1.1; PyInstaller 6.22.3; hooks 2026.8; setuptools 84.0.0; resvg-py 0.5.0 |
| Codex | Official Windows x86_64 0.160.0 CLI, managed daemon and installed extension binary |
| VS Code | 1.140.0; official openai.chatgpt 26.930.41038 |
| Defaults | All interactive clients; 24h lookback; 30s poll; Continue; Private telemetry; tracing off; 8 MiB/three gzip backups |

## Compatibility certification

The certified CAC 0.4.0 tuple is Windows x86_64, CLI 0.160.0 and managed daemon 0.160.0. Both EXE SHA-256 values are `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`. The consumer-schema SHA-256 is `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`. [Compatibility](COMPATIBILITY.md) owns policy and identity limits.

The complete official CLI package was fetched through the CI downloader into ignored staging. Its GitHub-published size and SHA-256 passed before extraction: `7f7fbbc8d6fd4ea2f3b13855ef47ea59663ba7e61fb2e9821df37163b8030891`. Its extracted binary matches the installed CLI/daemon/extension. The official latest stable API also reported rust-v0.160.0 during this run. No user installation, account or updater setting was changed by these probes.

| Check | Observed result |
| --- | --- |
| Regular Windows gate | 194 passed in 33.81s; compileall and 0.4.0 import passed |
| Native continuation gate | 10 passed in 74.35s against the downloaded complete official package |
| Installed extension gate | One scenario passed in 14.96s; all eight client combinations, quota denial, one original-owner Continue/completed turn, no duplicates, Private telemetry and original-file hashes |
| Consumer schema | Native generated contract matches the packaged projection and certificate; prerelease/build suffixes are retained; separate-package bootstrap/schema follow-up passed: two cases in 13.87s |
| Unit safety | Unknown tuple, queue/read drift, identity mismatch, same-version file replacement, reconnect revalidation and before-send version change block mutations; pending/uncertain state survives |
| Download boundary | Traversal, absolute/drive paths, links, case collisions and extracted-size limits are rejected before extraction |

The managed native case uses production discovery, handshake, managed-binary schema and certification. It survives a real daemon restart, deliberately removes certification, records no send and preserves the exact pending-state bytes. Restoring certification permits one saved Continue on the separate original writer. Three later scans produce no duplicate. Updater and remote control are disabled only in the disposable home. Native Codex must create private Windows socket/state directories; Python-created inherited permissions were rejected during fixture development.

The follow-up used the installed CLI and the separately downloaded complete CLI package as the managed candidate, exercising CI's package-copy/bootstrap path. Both have the certified 0.160.0 identity; this is not evidence for different-release mixed behavior.

The separate official `codex-app-server.exe` 0.160.0 package was also inspected. Its version output and option-only help expose no schema generator. Eight controlled queue scenarios passed, but managed bootstrap failed because Codex expected `current/bin/codex.exe`. That package is not certified or used by managed CI. CAC rejects the standalone identity, even with a matching CLI version or synthetic certificate; it never substitutes the CLI's schema.

The eight other recovery cases cover quota failure, expired advisory reset, account/user mismatch, manual progress, edited/invalid prompts, multi-chat permission rechecks and accepted/unaccepted ambiguous writes. [Native continuation tests](CONTINUATION-TESTS.md) owns full settings and assertions. All credentials and chats are synthetic; account/model services are loopback-only. No real allowance is spent.

## Commands and bounds

```powershell
pwsh -NoProfile -File scripts/verify-windows.ps1
pwsh -NoProfile -File scripts/verify-continuation.ps1 -CodexPath 'C:/probe/package/bin/codex.exe'
pwsh -NoProfile -File scripts/verify-vscode.ps1 -CodePath 'C:/path/to/Code.exe' -ExtensionPath 'C:/path/to/openai.chatgpt-version-win32-x64'
& ./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('scripts/probe-compatibility.py','--codex-executable','C:/probe/package/bin/codex.exe','--report','.data/reports/schema.json') -TimeoutSeconds 40
```

Regular pytest is bounded at 180 seconds, compileall at 120, version checks at 30, native integration at 240 and extension integration at 180. Managed bootstrap/restart allow 25 seconds and stop 15. Schema generation allows 20. The official-package downloader has a 180-second transfer deadline and a 240-second outer bound. Fixture homes and owned native processes cleaned up; deployed CAC processes were unchanged during integration.

## Release checks

The release remains one portable folder with two EXEs and `_internal`, a short guide, original notices and per-file hashes. The generated contract and Codex attribution ship; development docs, tests, audits, runtime data and downloaded probe packages do not.

The frozen UX probe checks implicit defaults, spaces/percent in paths, exclusive controls, correlated scan feedback, same-PID reload, invalid-settings/prompt pause and repair, graceful stop and zero Codex connections. One early run timed out waiting for an invalid-prompt phase; its retry passed. The probe now reports sanitized phase/event context on timeout. No unverified runtime fix was applied for that single transient observation.

Final frozen probe passed with all 525 release-file hashes and ZIP CRC verified. It tested same-PID settings/prompt pause and repair, scan acknowledgement, controls and graceful stop in a path containing spaces and percent. It recorded zero Codex connections and zero user-chat dispatches. An earlier retry also passed. The one preceding invalid-prompt timeout was not reproduced; its cause remains unestablished.

The installed App was updated after graceful monitor stop and exact tray/process identity checks. All eight runtime files matched saved hashes before activation. Settings, Continue prompt, pending state, logs and Windows login path were preserved. The previous App remains in an ignored recovery folder. All 525 deployed hashes, wheel module/asset/contract parity, dependency notices and repository Markdown targets passed.

The new tray and supervisor are running. The frozen live-status command reports 0.4.0, monitoring and certified 0.160.0 CLI/daemon, with zero pending/dispatched work at the sampled cycle. All three clients, Detailed local logging and startup remain enabled. No user chat was forced to continue for testing.

| Artifact | SHA-256 |
| --- | --- |
| `dist/codex-auto-continuer-0.4.0-windows-x86_64.zip` | `be6bdbe6481caf10bd61ede8dddd39f81c257162010281263c0c6b734f49499a` |
| `dist/codex_auto_continuer-0.4.0-py3-none-any.whl` | `c903b469dcd8ad7509a8336264e96e52a5d1275a9412a4e1a4fd6891c7bae624` |

Portable size: 16,316,196 bytes; 526 ZIP entries including the manifest. Wheel: 85,819 bytes; 34 entries. The stable source transport is `codex-auto-continuer-codex-handoff.zip`, with generated checksums and Git provenance. Builds are not claimed byte-for-byte reproducible.

## CI and publication

The regular Windows build workflow and new scheduled compatibility workflow use commit-pinned official actions, read-only permissions and no persisted checkout credentials. Compatibility runs daily, manually, on pull requests and default-branch pushes, with baseline, current-stable and independently updated daemon cases. Passing CI never changes certificates automatically. Sanitized reports expire after 14 days.

The pre-commit privacy probe inspected all nine existing commits, 224 unique Git blobs and 117 source files. No credential-shaped values, personal profile/project paths, private author emails, tracked runtime files or broken Markdown links were found. Deep inspection covered both new EXEs, 441 bytecode modules/code filenames, and the 34-entry wheel. Source transport is refreshed and inspected again after the scoped commit. Audit retention deleted nothing.

GitHub-hosted execution remains unobserved because this checkout has no remote and has not been uploaded. Local native results do not claim a hosted pass or an active GitHub schedule. One public repository retains sanitized Git-tracked audits/manifests; no history rewrite or upload is performed.

## Remaining limits

- No natural OpenAI quota-reset delivery or visual VS Code webview rendering was observed. Native recovery and installed extension ownership passed controlled tests.
- Current stable equals the certified baseline. Actual different-release mixed behavior awaits a future stable version; unit tests cover conflicting identities now.
- The gate certifies the discovered CLI/managed-daemon tuple, not an undisclosed binary behind every separate writer. Disk checksums and the running version cannot attest already-loaded bytes after an out-of-band same-version replacement.
- Queue addition has no verified atomic turn precondition or idempotency guarantee. Subsequent-turn metadata is an observation, not certain attribution.
- Shortcut launch is not a fresh Windows login; native UI checks are not a full manual accessibility review. EXEs remain unsigned.
- Downloaded probe packages remain in ignored `.data` staging because the host rejected recursive cleanup. They are excluded from Git, app releases and source transports.
