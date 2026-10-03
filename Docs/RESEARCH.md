# Research and provenance

Verified on 3 October 2026 using native Windows 11 (10.0.26300), PowerShell 7.6.6, Python 3.13.7 and Codex CLI/app-server 0.160.0. The reviewed base is ChatGPT checkpoint v001, whose 46 file hashes matched before local edits. Exact checks belong to [VALIDATION.md](VALIDATION.md). Probe source and essential results are in [the dated audit](Audits/2026-10-03/AUDIT.md).

## Authoritative interface evidence

The installed CLI generated its own experimental JSON schemas with:

```powershell
codex app-server generate-json-schema --experimental --out .data/schema
```

Generated schemas are temporary reference data, excluded from source transports. Relevant observed fields and methods are recorded here and in the audit.

[Official OpenAI app-server documentation](https://learn.chatgpt.com/docs/app-server) describes schema generation, initialization, thread/turn lifecycle and approval requests. The installed schema and native probes establish the experimental queue and recovery fields used by this project. General documentation alone does not establish their complete contract.

## Native socket transport

Standard Windows Python does not export `socket.AF_UNIX`. Windows Winsock does support family 1. Native tests and live connections passed using a Python-owned socket with a small `ctypes` address-marshalling bridge.

The running daemon returned a private control socket and matching CLI/app-server versions, both 0.160.0. The WebSocket initialization, metadata reads, turn reads, queue RPCs and account rate-limit read succeeded through that socket.

## Desktop provenance

A live sample returned 74 non-archived interactive threads. Every sampled thread had `source = vscode` and `originator = Codex Desktop`. The initial custom-only Desktop filter would exclude this installation.

The runtime accepts this verified pair plus configured `chatgpt` and `atlas` custom sources. Ordinary VS Code extension threads remain excluded from default Desktop scope. Originator absence does not authorize accepting an arbitrary VS Code thread.

## Separate app-server ownership

The running Desktop app and managed daemon use separate app-server processes. On an owned probe thread, a separate server reported `notLoaded` even while the original server owned it. Resume returned JSON-RPC code `-32600` and the exact error:

```text
thread <exact-thread-id> already has an active writer
```

Queue submission through the daemon reached the original owner and produced a completed turn. This verified condition permits shared-queue dispatch without taking ownership. Other resume errors do not.

A separate native probe confirmed queue addition, listing and exact deletion while unloaded. Deleting the owned item preserved the unrelated probe item. Resume followed by queue submission also completed after the submitting client disconnected.

## Usage failure persistence

A temporary isolated Codex home used a localhost HTTP fixture returning 429 with `error.type = usage_limit_reached`. It used a non-secret fixture key and made no real account request.

The native server reported `status = failed` and `codexErrorInfo = usageLimitExceeded`. A persisted `thread/turns/list` read returned the same classification and a numeric `completedAt`. This verifies both structured detection and the 24-hour failure-time cutoff.

Persisted turn history can show `interrupted` while a live turn is still active. The unloaded probe waits for inactive runtime status before accepting a terminal result. Runtime discovery avoids active threads and revalidates the exact latest turn before sending.

## Recovery authority and delivery safety

The live account returned `ordinaryUsageAllowed = true`. Portable regressions cover false and null authority, reset hints without permission, rechecks after resume and between threads, stale cancellation, exact queue ownership and ambiguous-send refusal.

No verified queue-add idempotency contract was found. Deterministic client message IDs support reconciliation, not blind retries. The queue API has no verified compare-and-swap condition against the failed turn. A narrow race between final revalidation and queue acceptance remains.

## Observational limits

The installed supervisor observed a real usage-limit failure in the current Desktop chat. It detected one obligation, kept it pending through 9 scans with ordinaryUsageAllowed false, then cancelled it when the user manually resumed and a later read returned true. No continuation was dispatched. This verifies real detection, waiting and stale cancellation without duplicate work; it does not establish automatic continuation at natural recovery or the cause of availability recovery.

Two simultaneous quota-stalled threads were covered by regression fixtures, not two real-account failures. The native delivery and isolated failure-serialization probes establish the component paths separately.

The generated Windows login shortcut was launched and its background process verified. A fresh Windows login was not performed. Cross-version support remains guarded at runtime; this evidence establishes the tested 0.160.0 installation.
