# Project workflow

## Source ownership

The project is self-contained. `AGENTS.md` owns environment-specific instructions; `Docs/README.md` maps product contracts and evidence. `.project-workflow.json` declares the project name, required source anchors, interpreter used by Windows workflow wrappers and additional export exclusions. Helpers use standard-library Python 3.10+, independently of the product language.

`CHAT-MANIFEST.md` belongs to ChatGPT. `CODEX-MANIFEST.md` belongs to Codex. Read both when receiving work; record only your environment's work and checks. `local-bootstrap` means no canonical ChatGPT checkpoint has been imported yet. The first ChatGPT checkpoint replaces that identity; do not invent prior checkpoint history.

## Codex to ChatGPT

Run audit cleanup, run `pwsh -NoProfile -File scripts/verify-windows.ps1`, review docs, update the Codex manifest and commit scoped changes when safe. Then run:

```powershell
pwsh -NoProfile -File scripts/pack-codex-handoff.ps1
```

The packer runs audit retention and replaces one `<project>-codex-handoff.zip` beside `README.md`. It includes source, tests, relevant configuration, docs, helpers and audit evidence/state. `_HANDOFF_MANIFEST.json` records the base checkpoint, Git provenance, exact file set, sizes and SHA-256 hashes. Every entry is verified before replacement. The previous handoff remains available if validation fails.

Give the user the ZIP path. ChatGPT extracts the source into its sandbox, reads both manifests and the current audit, then continues from the supplied evidence. It must account for Codex's work before publishing the next canonical checkpoint.

Inspect project Git status after packaging. If retention pruned tracked audit data after the commit, review and commit those managed changes, then refresh the handoff again. The packer does not stage or commit source automatically.

## ChatGPT to Codex

After its checks, ChatGPT updates `CHAT-MANIFEST.md` with a new increasing ID, for example `v001`, then builds:

```sh
python3 scripts/project-workflow.py checkpoint --id v001
```

The source-only ZIP is created under `Checkpoints/`, contains `_CHECKPOINT_MANIFEST.json`, and is never overwritten. IDs start with a positive `v` number, optionally followed by a descriptive suffix. The builder rejects numbers no greater than the imported Codex base or existing local checkpoints. Persist the ZIP to the Library or another available durable attachment before the disposable sandbox ends. Codex does not create this canonical sequence.

On Windows, preview a received checkpoint outside the checkout:

```powershell
pwsh -NoProfile -File scripts/import-checkpoint.ps1 -ArchivePath 'E:\Downloads\project-checkpoint-v001.zip' -Preview
pwsh -NoProfile -File scripts/import-checkpoint.ps1 -ArchivePath 'E:\Downloads\project-checkpoint-v001.zip'
```

The importer requires a clean project Git subtree, not a clean parent repository. It rejects a handoff passed as a checkpoint, invalid paths, links, duplicate/case-colliding names, missing anchors, checksum mismatches and unowned conflicts. It supports monorepos and standalone Git repositories without hardcoded parent depth.

The importer takes a verified backup of replaceable source and audit state outside the checkout. It replaces owned source, removes owned source absent from the checkpoint, and leaves excluded runtime/cache data and unrelated files intact. Audit state is an explicitly owned transport file despite being Git-ignored. Source checksums detect corruption; they do not authenticate an archive from an untrusted sender. Review source before executing imported code.

The importer resets the Codex record to the imported base and marks native verification pending. Run the native gate, reconcile docs, commit only the project changes, then build the stable handoff. Keep the printed recovery backup until verification succeeds. An I/O interruption may leave a partial replacement; the error identifies the backup. Do not repeatedly import over an unexplained partial state.

## Export boundaries

Both builders exclude `.git`, local databases/telemetry in `.data/`, virtual environments, package installations, `node_modules`, build output, caches, temporary files, locks, `.env`, `Checkpoints/`, `Handoffs/` and prior transport metadata. Toolchain/vendor infrastructure under `Reference/` is excluded. Add project-specific secrets or runtime directories to configuration; do not assume every secret has a recognisable filename.

Exports walk the relevant tree rather than relying on Git ignore rules. This intentionally includes ignored audit retention state and useful untracked evidence. Archive paths must work on both Windows and Linux. The source-only transport has a 128 MiB extracted-size limit and a 10,000-entry safety limit; imports also reject ZIPs larger than 256 MiB before opening their directory. If it exceeds those limits, remove duplicated/generated output before changing policy. Never silently drop requested evidence.

`Docs/History/` contains completed long-lived records. [`Audits/README.md`](Audits/README.md) owns the current dated audit and its shorter retention policy. Packaging runs cleanup but does not rotate the current audit. Maintenance is invocation-driven, not a background scheduler.
