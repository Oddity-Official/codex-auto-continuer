#Requires -Version 7.0
[CmdletBinding()]
param(
    [ValidateSet('focused', 'verify', 'native', 'build')][string] $Mode = 'focused',
    [string[]] $Tests = @('tests'),
    [string] $CodexPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Create the project .venv and install .[dev] first; see CONTRIBUTING.md.' }
switch ($Mode) {
    focused { & "$PSScriptRoot/run-project-command.ps1" -FileName $python -Arguments (@('-m','pytest','-q','--durations=5') + $Tests) -TimeoutSeconds 90 }
    verify { & "$PSScriptRoot/verify-windows.ps1" }
    native {
        if (-not $CodexPath) { throw 'Supply -CodexPath with the complete official Codex executable; see Docs/CONTINUATION-TESTS.md.' }
        & "$PSScriptRoot/verify-continuation.ps1" -CodexPath $CodexPath
    }
    build { & "$PSScriptRoot/build-portable.ps1" }
}
