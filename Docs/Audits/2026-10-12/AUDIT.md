# Codex Auto Continuer audit

Audit date: 2026-10-12
Started at: 2026-10-12T17:29:35.692650+00:00

## Scope and decisions

Review public-facing documentation and all reachable Git history before exposing the existing GitHub repository. The user explicitly waived another machine/VM and fresh-install/login acceptance for this initial public release. No runtime change, release rebuild, client interaction or user-data mutation is required. CAC 0.7.6 retains its prior native, frozen, signed-update and installed acceptance evidence.

The user reviewed the historical Windows profile-name test canary and approved leaving it public after considering sanitization. No history rewrite, private archive or second contribution repository is being created. The profile-name exposure is accepted, not reported as absent.

## Full-history privacy review

After fetching all remote tags, the private repository contains 61 reachable commits, 1,184 objects and 758 unique blobs totaling 9,187,196 bytes. All branches and release tags are in scope. The only author address is the account's public GitHub noreply address; no private author email or tracked runtime/authentication/environment/deployment path was found.

Official Gitleaks 8.30.1 was downloaded from its publisher's release and checked against that release's SHA-256 list. Windows x64 archive SHA-256: `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`. It is a local audit tool, not a CAC dependency or shipped asset.

The redacted scan used `gitleaks git . --log-opts="--all --full-history" --ignore-gitleaks-allow --redact=100 --no-banner --no-color --report-format=json --report-path=<ignored-local-report> --timeout=120`. It scanned 61 commits and approximately 1.85 MB of patches, returning exit 1 for one private-key finding. Direct inspection established a false positive: the historical archive inspector defines literal BEGIN PRIVATE KEY/RSA PRIVATE KEY/OPENSSH PRIVATE KEY headers to reject leaked keys. It contains no private-key body. The finding is reviewed, not suppressed by disabling key detection or adding a broad allowlist.

A separate byte-level review covered every reachable blob, including binary and UTF-16 profile-marker forms. One historical helper blob carries the accepted profile-name canaries. Two historical versions contain only the reviewed key-header detection strings. No credential material was identified. Matching private runtime metadata against all historical objects found zero matches among 225 observed thread/turn/queue identifiers. Thirty authoritative titles were checked; the only match is this project's own public name, Codex Auto Continuer. No private chat title matched.

Raw runtime canaries and local reports remain under ignored `.data`; they are never added to audit evidence or public source. This is a detector and known-canary review, not a mathematical guarantee that arbitrary undiscovered sensitive text cannot exist.

## Documentation and delivery

The README now describes the packaged 0.160.0/0.160.0 exact certificate rather than claiming retired certificates for 0.161.0. Public downloads need no GitHub login; optional private-publisher authentication is documented separately. The user guide, update owner and navigation agree. The 7 October audit was rotated into History and active links were repaired; dated historical commands and observations remain unchanged.

Existing 0.7.6 binary assets remain unchanged. Public release notes provide current launch/update guidance without introducing a documentation-only binary release. Anonymous access, visibility and final transport acceptance are pending.
