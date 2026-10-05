# Codex Auto Continuer

CAC 0.6.0 continues the exact local Codex chat stopped by a usage limit, once Codex confirms ordinary usage is available. It does not click windows, change the clipboard or answer approvals.

## Get started

1. Extract the whole folder to a writable location. Keep both EXEs and `_internal` together.
2. Launch `CodexAutoContinuer.exe`. Monitoring starts automatically. Look in Windows' hidden tray icons if needed.
3. Right-click the icon. `Start With Windows` launches CAC and starts monitoring at login for this Windows account, without administrator rights. A previous session's saved error does not suppress a new start; invalid current settings still require repair.

You need Windows 11 x86_64 and a signed-in native Codex installation. Python is bundled. Codex 0.160.0 is certified. Balanced mode also permits unknown stable builds after identity, schema and runtime checks. Strict mode requires exact certification. These independent EXEs are unsigned, so Windows may show a reputation warning.

## Tray controls

- `Status` shows the current state, last scan, chats checked, new quota failures, continuations sent and pending work. Double-click also opens it.
- `Start Monitoring` and `Stop Monitoring` control recovery. Stop finishes the current cycle and preserves pending work.
- `Clients To Monitor` independently selects VS Code, CLI and Desktop. `All` selects all three. No selection pauses client monitoring. Executor and sub-agent jobs are always excluded.
- `Modify Prompt` opens the saved Markdown prompt in its associated editor. The default is simply `Continue`.
- `Modify Settings` opens `data/settings.toml`, creating an annotated template if missing. Uncomment a setting to override its built-in default. Save as UTF-8; valid changes apply automatically between cycles. Invalid settings or prompts pause continuation until repaired.
- `Open Data Folder` opens settings, prompt, local status, pending state and logs.
- `Telemetry` explains and confirms Detailed or Private logging. `Restore Defaults` resets settings to Private logging while preserving the selected prompt, pending state, existing logs and login shortcut.
- `Exit CAC` gracefully stops monitoring and closes the tray.
- `Check For Updates` checks and installs a newer signed stable CAC release. Downloads do not block monitoring controls.

Green means monitoring, including waiting for quota. Yellow means stopped, starting, paused or reconnecting. Red means continuation is blocked by an error. Select `Status` for guidance.

Status shows compatibility evidence and policy. Unknown stable builds get one non-modal notice; working Balanced mode stays green. Set `compatibility_policy = "strict"` for exact-build-only recovery. A real compatibility block preserves pending work and allows only verified reads. CAC never changes Codex's installation or updater settings. `status --live` includes exact versions and checksums.

File actions do not wait for monitoring controls. If Windows has no file association, CAC opens the file in Notepad; other launch errors are reported, not hidden.

## Local recovery and privacy

Only structured `usageLimitExceeded` failures completed within the last 24 hours are discovered, including failures before launch. Recorded obligations stay pending beyond that window. Manual progress cancels stale work. Only Codex's explicit ordinary-usage permission authorizes a continuation; reset countdowns do not.

Coverage requires clients to share the same native Codex home and account. Remote, cloud and WSL chats are not covered. The local queue is experimental: an unresolved ambiguous send isolates that chat without a retry; other safe chats continue. Status and local telemetry explain it. Do not delete `state.json` to force a retry.

CAC does not upload diagnostics. `telemetry.jsonl`, `tray.jsonl` and `updates.jsonl` contain compact scan summaries, metadata changes, RPC timings, recovery decisions, compatibility evidence, update checks/replacement phases, errors and subsequent-turn observations. Private mode uses keyed identifiers and omits chat names and paths. Detailed mode retains real identifiers, names and paths. Neither records conversation bodies, prompt text, credentials, raw RPC payloads or exception locals.

Each stream defaults to 8 MiB plus three compressed backups. Advanced `diagnostic_trace` settings add allowlisted per-request summaries, independently of privacy. Changing privacy does not scrub old logs. Files are not encrypted; pending state still contains real chat IDs. Share the clean ZIP, not a used data folder.

## Optional queue holding

`Queue Holding > Enable Owner-Supported Holding`, or `holding on` in the CLI, enables this mode after the tray explains its coverage and private storage. The default is off.

CAC must already be observing an active chat on its connected native server owner before follow-ups arrive. Only that owner's dispatch lock can protect removal. A separate Desktop/extension/CLI owner, stdin/stdout owner, idle input or boundary before the observer connects is not protected. There are at most 16 simultaneous active subscriptions; Status shows their count and coverage warnings. Standard quota recovery remains available for unsupported chats. This is not a universal composer interceptor.

Captured requests and embedded attachments are encrypted in `data/held-inputs.dpapi` for the current Windows account and bound to the Codex home/account. Only queued input is stored, not the full conversation. Telemetry contains IDs, phases and decisions, never these bodies. The journal permits at most 1,000 requests and 32 MiB of plaintext; capture stops with a diagnostic before deleting input if it cannot persist safely. Keep this file until requests are delivered or explicitly discarded. Do not send it with diagnostics or a shared release.

During a usage stop, CAC sends the saved `Continue` unchanged. After that turn completes successfully, it releases the next held request, checks usage again and waits for terminal completion before releasing another. Ordinary successful work does not need an extra Continue. A request appearing in history is evidence of consumption, not successful completion. Exact client message IDs establish identity; duplicate text does not.

The submenu refreshes its request controls in the background. `View Private Input` reveals text only in an owned dialog; attachment bodies are retained but not dumped into the dialog. `Resume After Review` approves newer/manual progress, without bypassing quota, scope or completion checks. `Discard Unsent Input` deletes only a confirmed unsent recovery copy. For an unconfirmed removal/send, inspect the original chat **and its native queue** before choosing `Confirm Not Consumed` or `Confirm Consumed`. An incorrect manual resolution can duplicate or discard work. Remaining requests require separate resume approval. The menu shows the first 20 requests; the CLI lists all:

```powershell
.\CodexAutoContinuer-CLI.exe held list
.\CodexAutoContinuer-CLI.exe held list --show-input  # Explicit private body access in this terminal.
.\CodexAutoContinuer-CLI.exe held resume <thread-id>
.\CodexAutoContinuer-CLI.exe held discard <input-id>
.\CodexAutoContinuer-CLI.exe held confirm-unsent <input-id> --confirm
.\CodexAutoContinuer-CLI.exe held confirm-consumed <input-id> --confirm
.\CodexAutoContinuer-CLI.exe holding off
```

Stopping monitoring, disabling holding or restoring settings preserves held requests; it does not blindly put them back in Codex's queue. Turn holding back on to permit release. Unknown acknowledgement outcomes remain preserved without automatic retry. Original-client approval/input requests cause the observer to disconnect without answering; use Codex's original client, then review held requests.

## Terminal and portability

Portable CAC checks GitHub releases every 6 hours by default. `auto_update = false` makes updates manual. Installation waits for the current cycle, preserves data, backs up code and restarts at the same path. Failure restores code, never old continuation state. `update-status.json` names the recovery job; an interrupted installation can be recovered from its staged CLI with `update recover <absolute-job.json-path>`.

The publisher repository is private during testing. `update_use_github_cli_auth = true` uses an existing `gh auth login` for private releases. The token stays in memory, goes only to GitHub's API and is never bundled or logged. Public releases need no login. GitHub receives ordinary release requests and CAC's version, not chat data. Source and pip installations use their package manager instead.

`CodexAutoContinuer-CLI.exe --help` lists controls. Useful diagnostic commands are `status`, `status --live`, `scan`, `once` and foreground `run`. `scan` acknowledges its request and prints completed counts; it can send an eligible continuation, not just preview. Use `--config 'D:\My folder\settings.toml'` before the command for another data location.

Quit before moving an installed folder. Move its `data` with it, launch from the new location and re-enable `Start With Windows` to update the login shortcut. Small single-instance control files remain under `%LOCALAPPDATA%\CodexAutoContinuer`.

Our code is MIT licensed. `Licenses/` contains dependency notices and pystray's corresponding source. `RELEASE-MANIFEST.json` contains per-file SHA-256 hashes. Developer documentation, tests and audits stay in the source repository and source handoff, not this release.
