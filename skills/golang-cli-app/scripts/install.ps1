# Golang CLI App Skill Installer (Windows PowerShell)
# Usage: .\install.ps1 [-System | -Project] [-Agent <name>]
#
# Examples:
#   .\install.ps1 -System                    # Install to all system agent dirs
#   .\install.ps1 -System -Agent claude-code # Install to claude-code system dir only
#   .\install.ps1 -Project                   # Install to current project

param(
    [switch]$System,
    [switch]$Project,
    [string]$Agent = "",
    [switch]$Help
)

$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SkillName = Split-Path -Leaf $SkillRoot

if ($Help) {
    Write-Host "Golang CLI App Skill Installer (Windows)"
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [-System | -Project] [-Agent <name>]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -System     Install to system skill directories"
    Write-Host "  -Project    Install to current project directory"
    Write-Host "  -Agent      Target specific agent (claude-code, kimi, codex, opencode)"
    Write-Host "  -Help       Show this help message"
    exit 0
}

if (-not $System -and -not $Project) {
    Write-Host "Error: Must specify -System or -Project" -ForegroundColor Red
    exit 1
}

function Check-Go {
    $goExe = Get-Command go -ErrorAction SilentlyContinue
    if ($goExe) {
        $version = go version
        Write-Host "[OK] Go found: $version" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Go is not installed." -ForegroundColor Yellow
    }
}

function Get-SystemTargetDirs {
    $dirs = @()
    switch ($Agent) {
        "" {
            $dirs += "$env:USERPROFILE\.config\agents\skills"
            $dirs += "$env:USERPROFILE\.claude\skills"
            $dirs += "$env:USERPROFILE\.kimi\skills"
            $dirs += "$env:USERPROFILE\.codex\skills"
            $dirs += "$env:USERPROFILE\.opencode\skills"
        }
        "claude-code" {
            $dirs += "$env:USERPROFILE\.claude\skills"
        }
        "kimi" {
            $dirs += "$env:USERPROFILE\.kimi\skills"
            $dirs += "$env:USERPROFILE\.config\agents\skills"
        }
        "codex" {
            $dirs += "$env:USERPROFILE\.codex\skills"
        }
        "opencode" {
            $dirs += "$env:USERPROFILE\.opencode\skills"
        }
        default {
            Write-Host "Error: Unknown agent '$Agent'" -ForegroundColor Red
            Write-Host "Supported agents: claude-code, kimi, codex, opencode"
            exit 1
        }
    }
    return $dirs
}

function Get-ProjectTargetDirs {
    return @(
        ".\.agents\skills",
        ".\.kimi\skills",
        ".\.claude\skills"
    )
}

function Install-SkillToDir {
    param([string]$TargetDir)

    $linkPath = Join-Path $TargetDir $SkillName

    if (Test-Path $linkPath) {
        Write-Host "  [SKIP] $SkillName already exists at $linkPath" -ForegroundColor Yellow
        return $false
    }

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    New-Item -ItemType SymbolicLink -Path $linkPath -Target $SkillRoot | Out-Null
    Write-Host "  [OK]   $SkillName -> $linkPath" -ForegroundColor Green
    return $true
}

Write-Host "Golang CLI App Skill Installer" -ForegroundColor Blue
Write-Host ""

Check-Go

Write-Host ""

if ($System) {
    Write-Host "Installing $SkillName to system directories..." -ForegroundColor Blue
    $targetDirs = Get-SystemTargetDirs
    $installed = 0
    $skipped = 0

    foreach ($dir in $targetDirs) {
        if (Install-SkillToDir $dir) {
            $installed++
        } else {
            $skipped++
        }
    }

    Write-Host ""
    Write-Host "System installation complete." -ForegroundColor Green
    Write-Host "  Installed: $installed"
    Write-Host "  Skipped: $skipped"
}

if ($Project) {
    Write-Host "Installing $SkillName to project directories..." -ForegroundColor Blue
    $targetDirs = Get-ProjectTargetDirs
    $installed = 0
    $skipped = 0

    foreach ($dir in $targetDirs) {
        if (Install-SkillToDir $dir) {
            $installed++
        } else {
            $skipped++
        }
    }

    Write-Host ""
    Write-Host "Project installation complete." -ForegroundColor Green
    Write-Host "  Installed: $installed"
    Write-Host "  Skipped: $skipped"
}

Write-Host ""
Write-Host "Skill installed: $SkillName"
Write-Host ""
Write-Host "The skill provides code examples and best practices for building Go CLI apps."
Write-Host "Agents will reference this skill when helping you create CLI applications."
