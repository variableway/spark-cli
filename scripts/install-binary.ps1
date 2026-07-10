# Install the just-built spark binary into ~/.local/bin in a way that keeps
# both `spark.exe` (Windows) and `spark` (no extension) in sync, so bash
# cannot pick up a stale shadow file.
[CmdletBinding()]
param(
    [string]$Source = "spark.exe",
    [string]$InstallDir = "$HOME\.local\bin"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
    Write-Host ("Source binary not found: {0}" -f $Source)
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# On Windows bash matches the extension-less file first when both exist,
# so we MUST keep them in sync. Drop any stale shadow first, then copy.
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $InstallDir "spark")
    Copy-Item -Force $Source (Join-Path $InstallDir "spark.exe")
    Copy-Item -Force $Source (Join-Path $InstallDir "spark")
    Write-Host ("Installed {0} -> {1}/spark.exe and {1}/spark" -f $Source, $InstallDir)
} else {
    Copy-Item -Force $Source (Join-Path $InstallDir "spark")
    Write-Host ("Installed {0} -> {1}/spark" -f $Source, $InstallDir)
}
