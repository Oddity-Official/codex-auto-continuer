#Requires -Version 7.0
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $root '.project-workflow.json') -Raw | ConvertFrom-Json
$python = (Get-Command py -CommandType Application -ErrorAction Stop).Source
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $python -Arguments @(
    ('-' + $config.windows_python), (Join-Path $PSScriptRoot 'project-workflow.py'), 'handoff'
)
