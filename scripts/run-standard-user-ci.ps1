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
if (-not ('CacCiBatchLogon' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class CacCiBatchLogon {
    [StructLayout(LayoutKind.Sequential)] struct Attributes {
        public uint Length;
        public IntPtr Root, Name;
        public uint Flags;
        public IntPtr Descriptor, Quality;
    }
    [StructLayout(LayoutKind.Sequential)] struct Text {
        public ushort Length, MaximumLength;
        public IntPtr Buffer;
    }
    [DllImport("advapi32.dll")] static extern uint LsaOpenPolicy(IntPtr system, ref Attributes attributes, uint access, out IntPtr policy);
    [DllImport("advapi32.dll")] static extern uint LsaAddAccountRights(IntPtr policy, byte[] sid, ref Text rights, uint count);
    [DllImport("advapi32.dll")] static extern uint LsaRemoveAccountRights(IntPtr policy, byte[] sid, [MarshalAs(UnmanagedType.U1)] bool all, ref Text rights, uint count);
    [DllImport("advapi32.dll")] static extern uint LsaNtStatusToWinError(uint status);
    [DllImport("advapi32.dll")] static extern uint LsaClose(IntPtr policy);
    static void Check(uint status) {
        if (status != 0) throw new Win32Exception((int)LsaNtStatusToWinError(status));
    }
    public static void Set(byte[] sid, bool grant) {
        var attributes = new Attributes { Length = (uint)Marshal.SizeOf<Attributes>() };
        IntPtr policy;
        Check(LsaOpenPolicy(IntPtr.Zero, ref attributes, 0x810, out policy));
        const string right = "SeBatchLogonRight";
        var text = new Text { Length = (ushort)(right.Length * 2), MaximumLength = (ushort)((right.Length + 1) * 2), Buffer = Marshal.StringToHGlobalUni(right) };
        try { Check(grant ? LsaAddAccountRights(policy, sid, ref text, 1) : LsaRemoveAccountRights(policy, sid, false, ref text, 1)); }
        finally { Marshal.FreeHGlobal(text.Buffer); LsaClose(policy); }
    }
}
'@
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
$batchGranted = $false
try {
    $user = New-LocalUser -Name $identity -Password $password -AccountNeverExpires -PasswordNeverExpires
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    $sid = [byte[]]::new($user.SID.BinaryLength)
    $user.SID.GetBinaryForm($sid, 0)
    [CacCiBatchLogon]::Set($sid, $true)
    $batchGranted = $true
    & (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName 'wevtutil.exe' -Arguments @('sl', 'Microsoft-Windows-TaskScheduler/Operational', '/e:true') -TimeoutSeconds 15
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
    $startupDeadline = [DateTime]::UtcNow.AddSeconds(30)
    $resultPath = Join-Path $directory 'result.json'
    $logPath = Join-Path $directory 'output.txt'
    while (-not (Test-Path -LiteralPath $resultPath) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $task = Get-ScheduledTask -TaskName $identity
        $info = Get-ScheduledTaskInfo -TaskName $identity
        if ($task.State -eq 'Ready' -and $info.LastRunTime -gt [DateTime]::Now.AddMinutes(-10)) { break }
        if (-not (Test-Path -LiteralPath $logPath) -and [DateTime]::UtcNow -gt $startupDeadline) { break }
    }
    $logPath = Join-Path $directory 'output.txt'
    if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Raw | Write-Host }
    if (-not (Test-Path -LiteralPath $resultPath)) {
        $task = Get-ScheduledTask -TaskName $identity
        Write-Host (Export-ScheduledTask -TaskName $identity)
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
    if ($registered) {
        Stop-ScheduledTask -TaskName $identity
        Unregister-ScheduledTask -TaskName $identity -Confirm:$false
    }
    if ($batchGranted) { [CacCiBatchLogon]::Set($sid, $false) }
    if ($user) { Remove-LocalUser -SID $user.SID }
}
