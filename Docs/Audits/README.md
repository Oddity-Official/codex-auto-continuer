# Audit workspace

Keep the current audit report, reproduction scripts, fixtures and measured results together here. Both Codex and ChatGPT use this workflow. Older implementation and investigation ledgers remain in `Docs/History/`.

## Start an audit

Run from the project root, using today's date in the user's timezone:

```powershell
py -3 scripts/manage-audits.py start --date 2026-09-29
```

On Linux, replace `py -3` with `python3`. Python 3.10 or later is required; maintenance uses only the standard library.

The script moves existing dated audit folders into `History/`, creates a dated folder with `AUDIT.md`, and applies retention. Repeated audits on the same date use `-02`, `-03` and later suffixes. It never overwrites or merges an audit.

Write the report and every useful audit script, fixture and result into the new folder. Record the reviewed commit or checkpoint, environment, commands, timeouts, settings, observed results, severity and limitations. Include rerun instructions and distinguish confirmed defects from concerns. Keep minimal reproductions and essential results in `AUDIT.md` itself: supporting files expire sooner than reports.

Use checkout-relative source references in the report so moving it into `History/` does not break them. Make helpers discover the checkout rather than hardcoding machine paths. Put compiler output in `target/`, not in the audit folder. Do not store dependency installations, caches, old ZIPs or repeated large diagnostic bodies here.

The workspace's `.gitattributes` disables line-ending conversion so source-position fixtures retain their original bytes on every host. Leave it in place when exporting or rotating evidence.

## Retention

Run maintenance before exporting a checkpoint or handoff:

```powershell
py -3 scripts/manage-audits.py cleanup --dry-run
py -3 scripts/manage-audits.py cleanup
```

Retention uses the audit folder's date, not filesystem modification times. This keeps the policy stable after Git checkout or ZIP extraction:

| Data | Retention |
| --- | --- |
| Current dated audit folder | Always retained, until the next audit archives it |
| Archived supporting files and subfolders | Removed once the audit is more than 7 days old; only the root `AUDIT.md` remains |
| Archived report and its folder | Removed once the audit is older than one calendar month, during a monthly cleanup |

Age is measured using the current UTC date. The first successful maintenance run checks monthly retention. Subsequent monthly checks run no earlier than one calendar month after the last successful monthly check. Month-end dates clamp to the last day of the next month. Boundaries are strict: exactly 7 days or one month old is retained. An audit archived after its retention limit can be pruned immediately.

`.maintenance.json` records the last successful run and monthly cleanup in UTC. It is excluded from Git but included in handoffs and checkpoints; preserve it across environments. Failed and dry runs do not advance it. Cleanup happens when invoked, not through a background scheduler. If nobody runs maintenance, nothing is deleted.

The script validates all managed paths before changing them. It refuses links, junctions, unrecognised audit folders, missing reports, archive collisions and corrupt or future-dated state. `.audit.lock` prevents simultaneous maintenance runs. If a run crashes, inspect the PID and confirm it has stopped before removing a stale lock. Never reset invalid state or delete unexpected files just to make maintenance pass.

When changing this workflow, run the deletion-safety regression suite with `py -3 -m pytest scripts/tests/test_manage_audits.py` (or `python3 -m pytest` on Linux). Pytest is a test dependency, not a maintenance dependency.

## Handoff

On Windows, `scripts/pack-codex-handoff.ps1` runs cleanup before packaging and includes this workspace and its retention state in the project's stable Codex handoff ZIP. It refuses to package if maintenance fails. It does not start or rotate an audit.

On ChatGPT, `python3 scripts/project-workflow.py checkpoint --id CHECKPOINT-ID` runs cleanup before creating the versioned project checkpoint. Set `CHAT-MANIFEST.md` to the new ID first. Include `Docs/Audits/`, including `.maintenance.json`, but exclude `.audit.lock`, temporary files, compiler output and caches. The report and evidence travel inside the normal project ZIP; do not create nested audit ZIPs.

Read the current audit before repeating its work. Reuse its sources and results, then add evidence where verification or a changed checkout requires it. Begin a new audit only when conducting a new audit, not merely when receiving a handoff or implementing its findings.
