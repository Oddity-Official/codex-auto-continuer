#Requires -Version 7.0
[CmdletBinding()]
param([string] $PythonPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This gate is for native Windows. Use python3 -m pytest tests scripts/tests -q in ChatGPT/Linux.' }
$root = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $root '.project-workflow.json') -Raw | ConvertFrom-Json
$runner = Join-Path $PSScriptRoot 'run-project-command.ps1'
$prefix = @()
if ($PythonPath) {
    $python = (Get-Command $PythonPath -CommandType Application -ErrorAction Stop).Source
} elseif (Test-Path -LiteralPath (Join-Path $root '.venv/Scripts/python.exe') -PathType Leaf) {
    $python = Join-Path $root '.venv/Scripts/python.exe'
} else {
    $python = (Get-Command py -CommandType Application -ErrorAction Stop).Source
    $prefix = @('-' + $config.windows_python)
}
Write-Host "Verification interpreter: $python $prefix"
$versionCheck = @"
import sys
expected = tuple(map(int, '$($config.windows_python)'.split('.')))
if sys.version_info[:len(expected)] != expected:
    raise SystemExit('Use Python $($config.windows_python) for this gate')
print(sys.version.split()[0])
"@
& $runner -FileName $python -Arguments ($prefix + @(
    '-c', $versionCheck
)) -TimeoutSeconds 30

& $runner -FileName $python -Arguments ($prefix + @(
    '-m', 'pytest', 'tests', 'scripts/tests', '-q'
)) -TimeoutSeconds 180

& $runner -FileName $python -Arguments ($prefix + @(
    '-m', 'compileall', '-q', 'src', 'tests', 'scripts'
)) -TimeoutSeconds 120

& $runner -FileName $python -Arguments ($prefix + @(
    '-c', "import sys; sys.path.insert(0, 'src'); import codex_auto_continuer; print(codex_auto_continuer.__version__)"
)) -TimeoutSeconds 30
