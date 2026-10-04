# Research and provenance

Reviewed on 3 October 2026 on native Windows 11, Python 3.13.7 and Codex CLI/app-server 0.160.0. The imported base was ChatGPT v001, with all 46 file hashes verified before local edits. Native 0.1.0 work is committed as `1ef490f`. Version 0.2.0 adds portable tray controls and metadata telemetry.

Current results belong to [VALIDATION.md](VALIDATION.md). Tray-release probes are retained in [the dated audit](Audits/History/2026-10-03-02/AUDIT.md). Earlier native evidence is retained in [the 0.1.0 audit](Audits/History/2026-10-03/AUDIT.md).

## Interface authority

The installed CLI generated experimental schemas with:

```powershell
codex app-server generate-json-schema --experimental --out .data/schema
```

These are temporary references, not exported runtime dependencies. [Official app-server documentation](https://learn.chatgpt.com/docs/app-server) describes the integration layer, initialization, thread/turn lifecycle and approval requests. Installed schemas and native probes establish the experimental queue and quota fields used here. General documentation does not establish a queue idempotency or atomic turn-precondition guarantee.

The guarded minimum version is 0.160.0. Only that installation has current native evidence. Required methods and fields are checked at runtime; a version number alone is insufficient.

## Verified native facts

Windows Python does not export socket.AF_UNIX, but Winsock supports Unix-domain sockets. The Python-owned socket plus ctypes address bridge passed native tests and real daemon connections.

A live Desktop sample contained 74 vscode-source chats with Codex Desktop originator. Source alone cannot distinguish Desktop from the extension. Independent client selection uses both; the default selects Desktop, VS Code and CLI.

A separately owned server reported notLoaded through the daemon. Resume returned -32600 with the exact thread's active-writer error. Shared-queue submission reached the original owner and completed. Unrelated resume errors remain fatal.

A second probe confirmed unloaded queue add/list/delete, exact deletion preserving another item, and completion after the submitting client disconnected. An isolated native localhost HTTP 429 fixture persisted failed/usageLimitExceeded with a numeric completedAt. It used a fixture key and made no real account request.

Persisted history can say interrupted while a live turn is active. Runtime active status takes precedence. Discovery ignores active threads, and delivery observations do not end until the runtime is inactive.

The [native continuation suite](CONTINUATION-TESTS.md) joins quota failure, account validation, durable CAC detection, waiting, native queue dispatch and completed-turn observation in one isolated chain. It uses unmodified Codex with local service responses and synthetic authentication. Wrong account or user identity yields null permission. Two failed chats exercise the between-dispatch permission check. These are controlled native results, not natural account-reset or client-UI observations.

The 0.2.0 real CLI probe launched one private interactive TUI with `--no-daemon`, read-only sandbox, approvals never and fixed no-tools token replies. It established source=cli, separate-writer ownership, an acknowledged queue ID and a completed second turn. The CLI still reported originator=Codex Desktop from this installation; CLI selection deliberately relies on its source.

## Client support and inference

The supported scope is local interactive CLI, VS Code and Desktop visible to one native Codex home/account. Executor and sub-agent sessions are explicitly excluded by the user.

Actual CLI delivery and Desktop-style separate-owner delivery have native evidence. On 4 October 2026, the installed official VS Code extension passed the [isolated extension-host gate](CONTINUATION-TESTS.md#installed-vs-code-extension). Its unchanged bundle launched and initialized its unchanged Codex executable. The resulting thread recorded `source=vscode` and `originator=codex_vscode`. All eight client-selection combinations classified it correctly. CAC waited through denied scans, then queued one Continue; the original extension-owned server completed the exact chat and subsequent scans did not duplicate it.

The test supplies initial thread/turn RPCs through an instrumented native transport, not a clicked composer. It proves real extension-owned recovery, not visual chat rendering. Generic app-server processes can also report `vscode`; the bucket is not a positive extension-originator allowlist. Explicit `appServer`, executor, sub-agent and unknown source labels remain excluded. Current versions and measurements belong to [verification](VALIDATION.md#vs-code-extension-owner).

Remote, WSL, cloud, different homes, accounts or users are separate environments. A native supervisor cannot assume visibility into them.

## Public tool survey

We searched public Codex quota recovery, auto-continue, auto-resume, queue, tray, usage and reset tools. We fetched the projects' own documentation. This is a broad discoverable survey, not an exhaustive inventory, security audit or performance comparison. [The README](../README.md#why-this-design-suits-us) owns the concise comparison.

The survey covered:

- [codex-charge](https://github.com/Autumnpoem/codex-autocontinue): CLI terminal wrapper and Desktop input automation, with tray controls
- [MrPanica watchdog](https://github.com/MrPanica/codex-auto-resume): native Windows accessibility invocation of retry controls, including broader transient errors
- [progressrdx auto-resume](https://github.com/progressrdx/codex-auto-resume): macOS selected-task recovery with task fingerprints and continuation bounds
- [auto-resume-trio](https://github.com/awslew/codex-auto-resume-trio): same-session structured CLI/app-server recovery, host service and dashboards
- [Claude Codex Queue](https://github.com/ravhello/claude-codex-queue): structured existing-task queues, ordered prompts and web/CLI controls; Windows instructions require WSL
- [claude-codex-auto-resume](https://github.com/TheOnlyFusionCube/claude-codex-auto-resume): configurable multi-tool terminal wrapper, reset-text parsing and resume modes
- [automode](https://github.com/adrielmendes28/automode): POSIX terminal wrapper, parsed usage resets, menu handling and scheduled auto-ping
- [Codex Dashboard](https://github.com/Justin1491/codex-dashboard): quota display and project auto-resume through executor resume-last
- [Perpetual](https://github.com/SakethSripada/Perpetual): VS Code orchestration across providers, cloud handoff and Docker
- [rate-tray](https://github.com/nowrap/rate-tray): native Windows quota display rather than exact-task recovery
- [Codex Companion](https://github.com/heycarollan/codex-usage-status): VS Code usage, remote controls, completion alerts and chat reopening
- [Limit Reset Tracker](https://codexlimitreset.com/): manually configured countdowns and reminders rather than account-connected task recovery

Structured targeting is not unique to this project. Our chosen fit is portable native Windows, existing interactive chats, quota-only authority, no UI input, simple Markdown editing and local diagnostics. The cost is dependence on guarded experimental Codex interfaces.

## Packaging choices

[pystray's public API](https://pystray.readthedocs.io/en/latest/usage.html) supplies native Windows menus and notifications. A project-owned SVG master generates state PNGs and the EXE icon at build time; Pillow loads and resizes them at runtime. No OpenAI artwork is reused. We do not implement a second tray framework.

[PyInstaller's folder mode](https://pyinstaller.org/en/stable/operating-mode.html) avoids repeated self-extraction and lets the bundled LGPL tray library remain replaceable. Matching tray source and original notices travel with releases. Builds happen in a virtual environment, not by changing unrelated globally installed dependencies.

## Observational limits

The earlier installed supervisor detected a real quota failure, waited through 9 unavailable-usage scans, then cancelled after the user manually resumed. No automatic continuation was dispatched. That is detection, waiting and stale-cancellation evidence, not a natural quota-reset delivery demonstration.

Two simultaneous real quota failures were not available. Regression fixtures cover multi-chat permission rechecks. A fresh Windows login was not performed; shortcut launch can be tested separately.

The API lacks verified atomic turn preconditions and queue-add idempotency. Immediate revalidation and exact stale deletion reduce risk without eliminating the narrow concurrent-progress race.
