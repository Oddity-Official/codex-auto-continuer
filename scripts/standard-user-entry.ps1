#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory)] [string] $RequestPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable Windows CI only.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Native daemon probes must run with a standard, non-elevated Windows token.'
}
Write-Host 'Native CI token: standard user (non-elevated).'
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
& (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $request.fileName -Arguments @($request.arguments) -TimeoutSeconds $request.timeout
