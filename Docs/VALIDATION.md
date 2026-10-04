# Verification

Current implementation: CAC 0.5.0, 4 October 2026, Windows 11 build 10.0.26300 x86_64, PowerShell 7.6.6 and CPython 3.13.7. Imported checkpoint: v001. [The dated 0.4.0 record](History/2026-10-04-native-0.4.0-validation.md) preserves previous release checks.

## Recovery and compatibility

The native recovery gate passed 11 scenarios in 88.45 seconds against official Codex 0.160.0. Both CLI and managed-daemon executable SHA-256 values are `fdda5fa3cf3fb3d000b876720742857676293e4315e4b045fae6f8bd7e866d1d`. The consumer-schema hash is `e738465218e57a4e519855347a7728e25813c148e4b09a5a4383cdf3b668dfeb`.

The managed test exercises production discovery, handshake, generated schema and restart identity checks. Removing its certificate proves Strict preserves pending-state bytes without submitting. Balanced then recovers the same untested stable tuple. Both scenarios verify one saved Continue on the separate owner and no later duplicate.

Unit regressions isolate one ambiguous chat while another continues, retain uncertain intent across later scans, and keep delivery observations when a separate owner's persisted terminal status has no completion timestamp. Real quota recovery in one Desktop chat was also observed; [dated natural evidence](History/2026-10-04-natural-recovery.md) records its causal limits.

## Update checks

The expanded Windows gate passed 223 tests in 33.93 seconds, with compileall and the 0.5.0 import check. Focused updater checks passed 27 tests in 4.20 seconds. Frozen release, private GitHub publication and real older-to-newer update/rollback checks remain in progress. These intermediate results do not assert release readiness.

The updater uses Ed25519 signed metadata, signed archive SHA-256, manifest file checks, bounded HTTPS and safe path extraction. Regression fixtures cover tampering, wrong publisher/platform/state schema, duplicate JSON keys, traversal, links, Windows device names, case collisions, authentication stripping on redirects, partial copying and interrupted backup moves. Rollback retains current data rather than restoring older queue obligations.

## Environment and limits

Runtime dependencies: pystray 0.19.5, Pillow 12.3.0, TOMLKit 0.15.1, six 1.17.0, Cryptography 48.0.1, CFFI 2.1.1 and pycparser 3.0. Build tools: PyInstaller 6.22.3 and resvg-py 0.5.0. No user Codex installation or authentication was changed by isolated probes.

The publisher repository is private and its signing key is not tracked. Public availability is not asserted. Ordinary verification and daily compatibility probes have read-only permissions; the separate stable release workflow has explicit publication permission and a signing secret.

Schemas cannot establish future queue semantics or atomic/idempotent submission. The running writer's executable bytes are not universally exposed by upstream. Update replacement is recoverable, not power-loss-atomic. A fresh Windows login and Windows reputation acceptance remain outside automated verification.
