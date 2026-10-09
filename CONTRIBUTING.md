# Contributing

Use native Windows 11 x86_64, PowerShell 7 and Python 3.13. Tests use synthetic chats and isolated control directories; they do not continue your Codex work. Linux checks do not prove Windows tray, startup or socket behavior.

## Set up and verify

Run from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 30 '.[dev,build]'
pwsh -NoProfile -File scripts/verify-windows.ps1
```

The gate selects `.venv/Scripts/python.exe` when present; otherwise it uses the configured `py -3.13`. `-PythonPath` selects another interpreter explicitly. It checks the Python version, runs pytest, compiles source and imports the application version. Commands have deadlines and process-tree cleanup. No second global dependency installation is needed.

For a focused check:

```powershell
pwsh -NoProfile -File scripts/dev.ps1 -Tests tests/test_supervisor.py
```

Add regressions for real failure modes, not implementation details. Keep recovery quota-only, exact-chat and fail-closed. Never add UI input, automatic approval answers or blind retries after ambiguous sends. [Architecture](Docs/ARCHITECTURE.md) owns these contracts.

Use `scripts/dev.ps1 -Mode verify` for the full local gate, `-Mode native -CodexPath 'absolute-codex.exe-path'` for isolated native recovery, and `-Mode build` for a portable candidate. Focused mode reports slow tests and does not build or install anything. [Workflow](Docs/WORKFLOW.md) owns completion tiers: prose-only changes still receive link checks and a source handoff, not unrelated builds. Hosted builds and native probes are filtered by consumed inputs; scheduled upstream checks remain independent. Exact equivalent CLI/daemon version tuples run once.

To exercise the actual native continuation chain with synthetic local service responses:

```powershell
pwsh -NoProfile -File scripts/verify-continuation.ps1
```

This separate gate requires native Codex, but no real login or allowance. It tests recovery, exact targeting, saved prompts, telemetry, multi-chat permission checks and ambiguous sends. [Native continuation tests](Docs/CONTINUATION-TESTS.md) explains isolation, deadlines and what is real versus simulated.

The development-only `psutil` dependency inventories fixture processes directly, avoiding PowerShell/CIM startup during teardown. Cleanup still verifies executable identity on the same Windows handle used to terminate private-package processes. `psutil` is not an application dependency or part of the portable runtime.

An opt-in [VS Code extension gate](Docs/CONTINUATION-TESTS.md#installed-vs-code-extension) uses your installed editor and extension in a disposable profile. It is separate from regular CI and the native recovery gate. [Compatibility](Docs/COMPATIBILITY.md) explains daily baseline, stable and mixed-daemon probes, and reviewed certificates.

## Run from source

```powershell
.\.venv\Scripts\python.exe -m codex_auto_continuer --help
.\.venv\Scripts\python.exe -m codex_auto_continuer tray
```

Source data lives in `.data/runtime`. A tray launch starts real monitoring. Use `clients = []` in a separate settings file before testing a supervisor against your installed Codex. Shared per-user locks prevent a second copy from monitoring alongside an existing app.

## Build a release

```powershell
pwsh -NoProfile -File scripts/build-portable.ps1
& ./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('scripts/build-wheel.py') -TimeoutSeconds 150
& ./scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('scripts/verify-portable.py') -TimeoutSeconds 180
$version = (& ./.venv/Scripts/python.exe -c 'from codex_auto_continuer import __version__; print(__version__)').Trim()
Get-FileHash -LiteralPath "dist/codex-auto-continuer-$version-windows-x86_64.zip" -Algorithm SHA256
```

The builder stages a fresh one-folder release, renders the SVG icon, bundles runtime licenses and pystray's corresponding source, and checks every manifest hash and ZIP CRC. It never copies an installed app or its data. Build-only tools and developer records do not ship. Unsigned EXEs may trigger Windows reputation warnings.

The wheel builder stages only current source and declared license inputs. It checks the exact package file set and bytes before replacing the output, so obsolete files in Setuptools' local `build/lib` cache cannot enter the wheel. Use `--out` for a separate inspection directory.

Before publishing, run the native gate and `scripts/verify-portable.py` as shown above. It checks the actual frozen package, including stale-status tray autostart and explicit encrypted-input review, in a disposable account-data location without Codex connections. Publish the clean versioned ZIP and its SHA-256, with the wheel only if wanted. Do not upload `App/`, `.data/`, a used `data/` folder or a ZIP made from a deployed app. CI artifacts are build results, not automatically approved releases.

Windows verification runs on pushes and pull requests with read-only permissions, no retained checkout credentials and commit-pinned actions. It needs no Codex login or signing secret. The separate [release workflow](Docs/UPDATES.md#publishing) runs from tags or manual dispatch, has publication permissions, and uses an Ed25519 signing secret only in its signing step. Never publish runtime data or developer staging.

## Documentation and local records

Keep public usage in [README](README.md) and the [portable guide](Docs/USER-GUIDE.md). Product, architecture and current verification each have one owner document. Link rather than copy changing facts. Record historical evidence with dates and checkout-relative references, never personal paths or chat names.

Audits, workflow helpers and ChatGPT/Codex manifests are public Git-tracked development records. They are useful provenance, not something contributors must operate to make an ordinary pull request. The checkpoint/handoff process is documented in [workflow](Docs/WORKFLOW.md); clean binary releases exclude it.

`.gitignore` and transport exclusions are separate safeguards. An ignored file can still be deliberately tracked; Git history can retain removed content. Before pushing, inspect staged files and commit history, and add any custom data locations to both exclusions. Follow [safe reporting](SECURITY.md) when sharing diagnostics.
