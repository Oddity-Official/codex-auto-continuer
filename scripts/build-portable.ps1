#Requires -Version 7.0
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Create .venv with py -3.13 -m venv .venv, then install .[dev,build] in it. See README.md.'
}
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $python -Arguments @(
    (Join-Path $PSScriptRoot 'build-portable.py')
) -TimeoutSeconds 360
