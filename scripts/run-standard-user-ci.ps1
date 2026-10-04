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
@{ fileName = $FileName; arguments = $Arguments; timeout = $TimeoutSeconds } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $request -Encoding utf8NoBOM
$password = ConvertTo-SecureString ([Guid]::NewGuid().ToString('N') + 'aA1!') -AsPlainText -Force
$user = $null
$process = $null
try {
    $user = New-LocalUser -Name $identity -Password $password -AccountNeverExpires -PasswordNeverExpires
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    & (Join-Path $PSScriptRoot 'run-project-command.ps1') -FileName (Get-Command icacls.exe).Source -Arguments @(
        $root, '/grant', "$($env:COMPUTERNAME)\${identity}:(OI)(CI)M"
    ) -TimeoutSeconds 30
    $service = Get-Service -Name 'seclogon'
    if ($service.Status -ne 'Running') {
        Start-Service -Name 'seclogon'
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(10))
    }
    $credential = [PSCredential]::new("$($env:COMPUTERNAME)\$identity", $password)
    $stdout = Join-Path $directory 'stdout.txt'
    $stderr = Join-Path $directory 'stderr.txt'
    $entry = Join-Path $PSScriptRoot 'standard-user-entry.ps1'
    $process = Start-Process -FilePath (Get-Command pwsh).Source -Credential $credential -LoadUserProfile -WindowStyle Hidden -WorkingDirectory $root -PassThru -ArgumentList @(
        '-NoProfile', '-File', ('"{0}"' -f $entry), '-RequestPath', ('"{0}"' -f $request)
    ) -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if (-not $process.WaitForExit(($TimeoutSeconds + 30) * 1000)) {
        $process.Kill($true)
        $process.WaitForExit(5000) | Out-Null
        throw 'The standard-user CI probe exceeded its deadline; its process tree was stopped.'
    }
    $process.Refresh()
    foreach ($path in @($stdout, $stderr)) {
        if (Test-Path -LiteralPath $path) { Get-Content -LiteralPath $path -Raw | Write-Host }
    }
    if ($process.ExitCode -ne 0) { throw "Standard-user CI probe failed with exit $($process.ExitCode)." }
}
finally {
    if ($process) { $process.Dispose() }
    if ($user) { Remove-LocalUser -SID $user.SID }
}
