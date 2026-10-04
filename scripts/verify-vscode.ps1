#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $CodePath,
    [Parameter(Mandatory)] [string] $ExtensionPath,
    [string] $PythonPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This extension integration gate requires native Windows, not WSL.' }
$root = Split-Path -Parent $PSScriptRoot
$python = if ($PythonPath) { (Get-Command $PythonPath -CommandType Application -ErrorAction Stop).Source } else { Join-Path $root '.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Create .venv and install .[dev] first, or pass -PythonPath.' }
$arguments = @('-m', 'pytest', 'integration/test_vscode.py', '-q', '-s', '--tb=short',
    '--vscode-executable', (Resolve-Path -LiteralPath $CodePath).Path,
    '--vscode-extension', (Resolve-Path -LiteralPath $ExtensionPath).Path)
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $python -Arguments $arguments -TimeoutSeconds 180
