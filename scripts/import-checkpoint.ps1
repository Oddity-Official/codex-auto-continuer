#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $ArchivePath,
    [switch] $Preview
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$archive = [System.IO.Path]::GetFullPath($ArchivePath)
$root = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $root '.project-workflow.json') -Raw | ConvertFrom-Json
$python = (Get-Command py -CommandType Application -ErrorAction Stop).Source
$arguments = @(('-' + $config.windows_python), (Join-Path $PSScriptRoot 'project-workflow.py'), 'import-checkpoint', $archive)
if ($Preview) { $arguments += '--preview' }
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $python -Arguments $arguments
