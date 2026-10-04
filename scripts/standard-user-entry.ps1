#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory)] [string] $RequestPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Disposable Windows CI only.' }
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
if ($request.kind -ne 'github-native-ci') { throw 'Not a native CI request.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Native daemon probes must run with a standard, non-elevated Windows token.'
}
$exitCode = 1
try {
    'Native CI token: standard user (non-elevated), outside the runner job.' | Set-Content -LiteralPath $request.logPath -Encoding utf8NoBOM
    & (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName $request.fileName -Arguments @($request.arguments) -TimeoutSeconds $request.timeout *>&1 |
        Out-String | Add-Content -LiteralPath $request.logPath -Encoding utf8NoBOM
    $exitCode = 0
}
catch { $_ | Out-String | Add-Content -LiteralPath $request.logPath -Encoding utf8NoBOM }
finally {
    $temporary = $request.resultPath + '.tmp'
    @{ exitCode = $exitCode } | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding utf8NoBOM
    Move-Item -LiteralPath $temporary -Destination $request.resultPath
}
exit $exitCode
