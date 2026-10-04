#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory)] [string] $RequestPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Disposable Windows CI only.' }
$directory = Split-Path -Parent $RequestPath
$logPath = Join-Path $directory 'output.txt'
$resultPath = Join-Path $directory 'result.json'
$exitCode = 1
try {
    'Native CI entry started.' | Set-Content -LiteralPath $logPath -Encoding utf8NoBOM
    $request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
    if ($request.kind -ne 'github-native-ci') { throw 'Not a native CI request.' }
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Native CI must be non-elevated.' }
    'Native CI token: standard user (non-elevated), outside the runner job.' | Add-Content -LiteralPath $logPath
    & (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $request.fileName -Arguments @($request.arguments) -TimeoutSeconds $request.timeout *>&1 |
        ForEach-Object { $_.ToString() | Add-Content -LiteralPath $logPath -Encoding utf8NoBOM }
    $exitCode = 0
}
catch { $_ | Out-String | Add-Content -LiteralPath $logPath -Encoding utf8NoBOM }
finally {
    $temporary = $resultPath + '.tmp'
    @{ exitCode = $exitCode } | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding utf8NoBOM
    Move-Item -LiteralPath $temporary -Destination $resultPath
}
exit $exitCode
