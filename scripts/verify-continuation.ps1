#Requires -Version 7.0
[CmdletBinding()]
param([string] $PythonPath, [string] $CodexPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This integration gate requires native Windows and Codex, not WSL.' }
$root = Split-Path -Parent $PSScriptRoot
$python = if ($PythonPath) { (Get-Command $PythonPath -CommandType Application -ErrorAction Stop).Source } else { Join-Path $root '.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Create .venv and install .[dev] first, or pass -PythonPath.' }
$arguments = @('-m', 'pytest', 'integration/test_continuation.py', '-q', '-s', '--tb=short')
if ($CodexPath) { $arguments += @('--codex-executable', (Resolve-Path -LiteralPath $CodexPath).Path) }
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $python -Arguments $arguments -TimeoutSeconds 240
