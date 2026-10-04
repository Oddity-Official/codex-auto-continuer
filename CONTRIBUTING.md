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
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('-m', 'pytest', 'tests/test_supervisor.py', '-q') -TimeoutSeconds 60
```

Add regressions for real failure modes, not implementation details. Keep recovery quota-only, exact-chat and fail-closed. Never add UI input, automatic approval answers or blind retries after ambiguous sends. [Architecture](Docs/ARCHITECTURE.md) owns these contracts.

## Run from source

```powershell
.\.venv\Scripts\python.exe -m codex_auto_continuer --help
.\.venv\Scripts\python.exe -m codex_auto_continuer tray
```

Source data lives in `.data/runtime`. A tray launch starts real monitoring. Use `clients = []` in a separate settings file before testing a supervisor against your installed Codex. Shared per-user locks prevent a second copy from monitoring alongside an existing app.

## Build a release

```powershell
pwsh -NoProfile -File scripts/build-portable.ps1
pwsh -NoProfile -File scripts/run-project-command.ps1 -FileName "$PWD/.venv/Scripts/python.exe" -Arguments @('-m', 'pip', 'wheel', '--timeout', '30', '--no-deps', '--no-build-isolation', '--wheel-dir', 'dist', '.') -TimeoutSeconds 120
Get-FileHash -LiteralPath 'dist/codex-auto-continuer-0.3.0-windows-x86_64.zip' -Algorithm SHA256
```

The builder stages a fresh one-folder release, renders the SVG icon, bundles runtime licenses and pystray's corresponding source, and checks every manifest hash and ZIP CRC. It never copies an installed app or its data. Build-only tools and developer records do not ship. Unsigned EXEs may trigger Windows reputation warnings.

Before publishing, run the native gate and the retained frozen-release probe described in [verification](Docs/VALIDATION.md). Publish the clean versioned ZIP and its SHA-256, with the wheel only if wanted. Do not upload `App/`, `.data/`, a used `data/` folder or a ZIP made from a deployed app. CI artifacts are build results, not automatically approved releases.

The GitHub workflow runs on Windows for pushes and pull requests. It uses read-only repository permissions, does not retain checkout credentials, pins actions to full commit hashes and uploads only named `dist` artifacts. It needs neither a Codex login nor repository secrets.

## Documentation and local records

Keep public usage in [README](README.md) and the [portable guide](Docs/USER-GUIDE.md). Product, architecture and current verification each have one owner document. Link rather than copy changing facts. Record historical evidence with dates and checkout-relative references, never personal paths or chat names.

Audits, workflow helpers and ChatGPT/Codex manifests are public Git-tracked development records. They are useful provenance, not something contributors must operate to make an ordinary pull request. The checkpoint/handoff process is documented in [workflow](Docs/WORKFLOW.md); clean binary releases exclude it.

`.gitignore` and transport exclusions are separate safeguards. An ignored file can still be deliberately tracked; Git history can retain removed content. Before pushing, inspect staged files and commit history, and add any custom data locations to both exclusions. Follow [safe reporting](SECURITY.md) when sharing diagnostics.
