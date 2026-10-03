#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $FileName,
    [Parameter(Mandatory)] [string[]] $Arguments,
    [ValidateRange(1, 600)] [int] $TimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Use the portable Python workflow in Linux; this runner is native Windows only.' }
# Keep Python -> .NET -> PowerShell -> redirected stdout UTF-8 end to end.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$info = [System.Diagnostics.ProcessStartInfo]::new()
$info.FileName = $FileName
$info.WorkingDirectory = Split-Path -Parent $PSScriptRoot
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$info.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$info.StandardErrorEncoding = [System.Text.Encoding]::UTF8
foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $info
try {
    if (-not $process.Start()) { throw "Could not start $FileName." }
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill($true)
        $process.WaitForExit(5000) | Out-Null
        throw "Command exceeded $TimeoutSeconds seconds and its process tree was stopped. Inspect the error and any stale workflow locks before retrying: $FileName $Arguments"
    }
    $output = $stdout.GetAwaiter().GetResult()
    $errorOutput = $stderr.GetAwaiter().GetResult()
    if ($output) { Write-Host $output.TrimEnd() }
    if ($errorOutput) { Write-Host $errorOutput.TrimEnd() }
    if ($process.ExitCode -ne 0) { throw "Command failed (exit $($process.ExitCode)): $FileName $Arguments" }
}
finally { $process.Dispose() }
