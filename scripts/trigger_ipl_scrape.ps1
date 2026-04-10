<#
.SYNOPSIS
    Triggers the IPL Fantasy Points scraper GitHub Actions workflow remotely.

.DESCRIPTION
    Uses GitHub CLI (gh) to dispatch the scrape_ipl.yml workflow on the main branch.
    Logs all output with timestamps to scripts/trigger_log.txt.
    Designed to be run by Windows Task Scheduler on a daily schedule.

.NOTES
    Prerequisites:
      - GitHub CLI installed: winget install GitHub.cli
      - Authenticated: gh auth login
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$LogFile = Join-Path $ScriptDir "trigger_log.txt"
$WorkflowFile = "scrape_ipl.yml"
$Branch = "main"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Entry = "[$Timestamp] [$Level] $Message"
    Write-Host $Entry
    Add-Content -Path $LogFile -Value $Entry
}

# --- Prerequisite checks ---

# 1. Check gh CLI is installed
$ghPath = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghPath) {
    Write-Log "GitHub CLI (gh) is not installed. Install with: winget install GitHub.cli" "ERROR"
    exit 1
}

# 2. Check gh is authenticated
try {
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "GitHub CLI is not authenticated. Run: gh auth login" "ERROR"
        Write-Log $authStatus "ERROR"
        exit 1
    }
} catch {
    Write-Log "Failed to check gh auth status: $_" "ERROR"
    exit 1
}

# --- Trigger workflow ---

Write-Log "Triggering workflow '$WorkflowFile' on branch '$Branch'..."

try {
    Push-Location $RepoRoot
    $output = gh workflow run $WorkflowFile --ref $Branch 2>&1
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -eq 0) {
        Write-Log "Workflow triggered successfully."
        Write-Log "Check status at: gh run list --workflow=$WorkflowFile --limit=1"
        exit 0
    } else {
        Write-Log "gh workflow run failed (exit code $exitCode): $output" "ERROR"
        exit 1
    }
} catch {
    Pop-Location
    Write-Log "Exception triggering workflow: $_" "ERROR"
    exit 1
}
