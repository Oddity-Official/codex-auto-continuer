#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $FileName,
    [Parameter(Mandatory)] [string[]] $Arguments,
    [ValidateRange(1, 600)] [int] $TimeoutSeconds = 300
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true') {
    throw 'This account-creating helper is restricted to disposable GitHub Windows runners. Use verify-continuation.ps1 locally.'
}
$root = Split-Path -Parent $PSScriptRoot
$identity = 'cac' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$directory = Join-Path $root ".data/standard-user-ci/$identity"
New-Item -ItemType Directory -Path $directory | Out-Null
$request = Join-Path $directory 'request.json'
@{ kind = 'github-native-ci'; fileName = $FileName; arguments = $Arguments; timeout = $TimeoutSeconds;
   logPath = (Join-Path $directory 'output.txt'); resultPath = (Join-Path $directory 'result.json') } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $request -Encoding utf8NoBOM
$plainPassword = [Guid]::NewGuid().ToString('N') + 'aA1!'
$password = ConvertTo-SecureString $plainPassword -AsPlainText -Force
$user = $null
$registered = $false
try {
    $user = New-LocalUser -Name $identity -Password $password -AccountNeverExpires -PasswordNeverExpires
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    & (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName (Get-Command icacls.exe).Source -Arguments @(
        $root, '/grant', "$($env:COMPUTERNAME)\${identity}:(OI)(CI)M"
    ) -TimeoutSeconds 30
    $entry = Join-Path $PSScriptRoot 'standard-user-entry.ps1'
    # Task Scheduler starts outside the runner's non-breakaway job object. Codex's
    # supported daemon launcher can then detach normally, without patching its guard.
    $action = New-ScheduledTaskAction -Execute (Get-Command pwsh).Source -WorkingDirectory $root -Argument (
        '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RequestPath "{1}"' -f $entry, $request
    )
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::FromSeconds($TimeoutSeconds + 30))
    Register-ScheduledTask -TaskName $identity -Action $action -Settings $settings -User "$($env:COMPUTERNAME)\$identity" -Password $plainPassword -RunLevel Limited | Out-Null
    $registered = $true
    Start-ScheduledTask -TaskName $identity
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds + 30)
    $resultPath = Join-Path $directory 'result.json'
    while (-not (Test-Path -LiteralPath $resultPath) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $task = Get-ScheduledTask -TaskName $identity
        $info = Get-ScheduledTaskInfo -TaskName $identity
        if ($task.State -eq 'Ready' -and $info.LastRunTime -gt [DateTime]::Now.AddMinutes(-10)) { break }
    }
    $logPath = Join-Path $directory 'output.txt'
    if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Raw | Write-Host }
    if (-not (Test-Path -LiteralPath $resultPath)) {
        $task = Get-ScheduledTask -TaskName $identity
        Write-Host ($task | Select-Object State, Principal, Settings | ConvertTo-Json -Depth 5)
        Get-WinEvent -FilterHashtable @{ LogName = 'Microsoft-Windows-TaskScheduler/Operational'; StartTime = [DateTime]::Now.AddMinutes(-10) } -ErrorAction SilentlyContinue |
            Where-Object { $_.Message -like "*$identity*" } | Select-Object -Last 10 -Property Id, Message | ConvertTo-Json | Write-Host
        Stop-ScheduledTask -TaskName $identity
        $info = Get-ScheduledTaskInfo -TaskName $identity
        throw ('The native CI task did not report completion. Task Scheduler result: 0x{0:X8}. Inspect the entry log; the task was stopped.' -f $info.LastTaskResult)
    }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    if ($result.exitCode -ne 0) { throw "Standard-user CI probe failed with exit $($result.exitCode)." }
}
finally {
    if ($registered) { Unregister-ScheduledTask -TaskName $identity -Confirm:$false }
    if ($user) { Remove-LocalUser -SID $user.SID }
}
