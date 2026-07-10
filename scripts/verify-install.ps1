# PowerShell install verification: prints sha256 + size + mtime for source and
# destinations, and exits non-zero if hashes disagree. Uses manual .NET SHA256
# because `Get-FileHash` is not available in PowerShell Core on Git Bash.
[CmdletBinding()]
param(
    [string]$Source = "spark.exe",
    [string]$InstallDir = "$HOME\.local\bin"
)

$ErrorActionPreference = "Stop"

function Get-SHA256([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $hasher.ComputeHash($bytes)
    } finally {
        $hasher.Dispose()
    }
    return ([BitConverter]::ToString($hashBytes)).Replace("-", "").ToLower()
}

function Get-FileInfo([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    $info = Get-Item $Path
    $hash = Get-SHA256 $Path
    return [pscustomobject]@{
        Path          = $info.FullName
        Length        = $info.Length
        LastWriteTime = $info.LastWriteTime
        Sha256        = $hash
    }
}

Write-Host ""
Write-Host "Install verification:"

$srcInfo = Get-FileInfo $Source
if ($srcInfo) {
    Write-Host ("  src: {0}  ({1} bytes, {2:yyyy-MM-dd HH:mm:ss}, sha256 {3})" -f $srcInfo.Path, $srcInfo.Length, $srcInfo.LastWriteTime, $srcInfo.Sha256)
} else {
    Write-Host ("  src: {0}  (missing)" -f $Source)
}

$dsts = @(
    (Join-Path $InstallDir "spark.exe"),
    (Join-Path $InstallDir "spark")
)
$dstHashes = @()
foreach ($d in $dsts) {
    $info = Get-FileInfo $d
    if ($info) {
        Write-Host ("  dst: {0}  ({1} bytes, {2:yyyy-MM-dd HH:mm:ss}, sha256 {3})" -f $info.Path, $info.Length, $info.LastWriteTime, $info.Sha256)
        $dstHashes += $info.Sha256
    } else {
        Write-Host ("  dst: {0}  (missing)" -f $d)
    }
}

if (-not $srcInfo) {
    Write-Host "  HASH MISMATCH: source not built"
    exit 1
}

$expected = $srcInfo.Sha256
if ($dstHashes -contains $expected) {
    Write-Host "  sha256 matches"
    exit 0
}

if ($dstHashes.Count -gt 1 -and ($dstHashes | Select-Object -Unique).Count -gt 1) {
    Write-Host "  HASH MISMATCH between destinations"
    exit 1
}

Write-Host ("  HASH MISMATCH src={0} dst={1}" -f $expected, ($dstHashes -join ","))
exit 1
