# Open validation work

Implementation is complete for the current v0.1 design. Remaining work is native/environment validation, not unimplemented fallback paths:

- Run `pwsh -NoProfile -File scripts/verify-windows.ps1` on the target Windows 11 machine.
- Exercise one real Desktop usage-limit → reset → same-thread continuation.
- Repeat with the target thread unloaded before reset.
- Exercise two simultaneously stalled threads and verify sequential rate-limit rechecks.
- Exercise manual progress while our continuation is still queued and verify live `thread/queue/delete` behavior.
- Verify per-user Startup launch with the user's actual Python and Codex install paths.

Any incompatible Codex behavior should be fixed at the structured interface/state-machine layer. Do not add UI automation as a fallback.
