# Audits

Each audit gets a dated folder here, such as `2026-10-15/`, holding `AUDIT.md` and every script, fixture and result it used. Repeated audits on the same date use `-02`, `-03` and later suffixes. When a new audit starts, move the previous one into `History/`. Nothing is deleted automatically.

Record the reviewed commit, environment, commands, timeouts, settings, observed results, severity and limits. Include rerun instructions, tell confirmed defects apart from concerns, and keep minimal reproductions in `AUDIT.md` itself. Use checkout-relative source references, so moving a report into `History/` doesn't break them. Make helpers find the checkout rather than hardcoding machine paths. Don't store dependency installations, caches, compiler output or old ZIPs here.

The workspace's `.gitattributes` turns off line-ending conversion, so source-position fixtures keep their original bytes on every host. Leave it in place.

Read the current audit before repeating its work. Start a new audit only when conducting one, not when implementing an earlier audit's findings.
