#Requires -Version 7.0
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This gate is for native Windows. Use python3 -m pytest tests scripts/tests -q in ChatGPT/Linux.' }
$root = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $root '.project-workflow.json') -Raw | ConvertFrom-Json
$python = (Get-Command py -CommandType Application -ErrorAction Stop).Source
$runner = Join-Path $PSScriptRoot 'run-project-command.ps1'

& $runner -FileName $python -Arguments @(
    ('-' + $config.windows_python), '-m', 'pytest', 'tests', 'scripts/tests', '-q'
) -TimeoutSeconds 180

& $runner -FileName $python -Arguments @(
    ('-' + $config.windows_python), '-m', 'compileall', '-q', 'src', 'tests', 'scripts'
) -TimeoutSeconds 120

& $runner -FileName $python -Arguments @(
    ('-' + $config.windows_python), '-c', "import sys; sys.path.insert(0, 'src'); import codex_auto_continuer; print(codex_auto_continuer.__version__)"
) -TimeoutSeconds 30
