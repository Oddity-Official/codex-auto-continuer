# Signed CAC updates

Portable CAC checks stable GitHub Releases every 6 hours and installs newer verified releases automatically. Set `auto_update = false` for manual updates. `Check For Updates` checks and installs a newer release; console equivalents are `update check` and `update apply`. Source and pip installations stay managed by their developer or package manager.

Failed automatic checks retry after 15 minutes, then return to the configured interval after success. Manual checks are available immediately. A failed update check does not mean Codex monitoring has stopped.

CAC updates itself, never Codex. Monitoring controls and editors stay responsive during downloads. Installation waits for the supervisor cycle, then restarts CAC at the same path while preserving stopped/monitoring intent. Turning off automatic updates during a download prevents automatic installation. Windows login shortcuts remain valid. Prompts, settings, pending obligations and telemetry are never replaced by release contents.

## Publisher and authentication

The trusted repository is `Oddity-Official/codex-auto-continuer`. The bundled `updates.json` pins its Ed25519 public verification key. Each release contains `UPDATE.json`, detached `UPDATE.sig`, the portable ZIP and optionally the source wheel. Cryptography verifies the signature before CAC trusts package identity, version, state schema, size or SHA-256.

Public releases need no GitHub login or GitHub CLI. Leave `update_use_github_cli_auth = false`, its default, for public downloads and updates.

For a private publisher repository, `update_use_github_cli_auth = true` uses an existing `gh auth login`. CAC reads the token into memory with a 5-second deadline; a timeout gets one further attempt bounded to 10 seconds. Missing GitHub CLI, launch failures and unusable logins receive distinct guidance without retries. CAC sends the token only to `api.github.com`, strips authentication on download redirects, and never saves, logs or bundles it.

GitHub sees normal release/download requests, your network address and CAC's version in its user agent. No chat identifiers, names, prompts, state or local diagnostics are uploaded. Update failures do not stop monitoring; Status and a deduplicated non-modal notice explain the issue.

## Verification and replacement

Downloads use HTTPS GitHub hosts only, bounded sizes and deadlines. ZIP validation rejects traversal, drive paths, links, duplicate or case-colliding paths, Windows device names and unexpected root components. The signed archive checksum and every release-manifest file checksum must match. Extracted files are checked again before installation.

An external worker runs from staging, not the app being replaced. It checks the exact app/config target and owns a per-user update lock. It stops only CAC's supervisor and verified tray process, never Codex. Process termination uses the same Windows handle used to check executable identity, protecting against PID reuse.

Code components move into a sibling `.cac-updates/<job>/previous` recovery folder before replacement. `data` and other user files stay in place. A durable journal records replacement intent before each copy. The new EXEs must pass file checks and a tray/CLI startup health check. A Codex compatibility block does not count as installation failure.

On a copy or health-check failure, the worker restores previous code and restarts it. It never restores old runtime state: that could forget a continuation already submitted. State schema 2 is required for automatic installation. An incompatible future state format needs a reviewed updater change, not a guessed migration.

## Recovery and limits

Replacement is recoverable, not an atomic multi-file transaction. Power loss can leave partial code until recovery runs. The installation result in `update-status.json` names its job and recovery folder; later release checks replace this latest-status snapshot. Durable jobs remain under `%LOCALAPPDATA%/CodexAutoContinuer/updates/<job>/job.json`, and code recovery journals remain beside the app in `.cac-updates/<job>/recovery.json`. Run a surviving CLI from the job's `bundle/CodexAutoContinuer` folder with `update recover <absolute-job.json-path>`. This replays rollback from the journal and retains current runtime data. Do not delete state or queue records to recover an installation.

Recovery/staging folders remain local for diagnosis and rollback. They are not in releases or source transports. Remove old completed recovery folders only after verifying that the current build and saved state work; never remove an in-progress job. Disk, permission, process-stop and rollback failures are reported rather than bypassed. CAC's EXEs are not Authenticode-signed; signed update metadata does not remove Windows reputation prompts.

## Publishing

`scripts/release.py key --install-secret` creates a publisher identity once. Its private key is encrypted for the publisher's Windows account under ignored `.data`; only its public key is tracked. GitHub Actions secret `CAC_RELEASE_SIGNING_KEY` holds the CI signing key. Do not regenerate it to fix a download failure.

The commit-pinned release workflow runs Windows and native recovery gates, builds clean ZIP/wheel assets, signs the exact ZIP and creates a draft release. It publishes only after all assets upload. Tags or manual workflow dispatch can trigger it; it never publishes pull-request code. Ordinary verification and compatibility jobs have read-only permissions and no signing secret. Certificates remain reviewed source changes, not publishing side effects.
