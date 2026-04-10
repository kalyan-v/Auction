<#
.SYNOPSIS
    Registers (or unregisters) the IPL Fantasy Scrape trigger as a Windows Scheduled Task.

.DESCRIPTION
    Creates a daily Windows Task Scheduler task that runs trigger_ipl_scrape.ps1 at 11:30 PM.
    Must be run as Administrator to register the task.

.PARAMETER Unregister
    Removes the scheduled task instead of creating it.

.EXAMPLE
    # Register the task (run as Administrator):
    .\setup_scheduled_task.ps1

    # Remove the task:
    .\setup_scheduled_task.ps1 -Unregister
#>

param(
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$TaskName = "IPL Fantasy Scrape Trigger"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TriggerScript = Join-Path $ScriptDir "trigger_ipl_scrape.ps1"
$TriggerTime = "23:28"  # 11:28 PM local time

# --- Unregister ---
if ($Unregister) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task '$TaskName' removed successfully."
    } else {
        Write-Host "Task '$TaskName' does not exist. Nothing to remove."
    }
    exit 0
}

# --- Prerequisite checks ---

# 1. Must be running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "Right-click PowerShell -> 'Run as Administrator', then try again."
    exit 1
}

# 2. Check trigger script exists
if (-not (Test-Path $TriggerScript)) {
    Write-Host "ERROR: Trigger script not found at: $TriggerScript" -ForegroundColor Red
    exit 1
}

# 3. Check gh CLI is available
$ghPath = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghPath) {
    Write-Host "WARNING: GitHub CLI (gh) is not installed." -ForegroundColor Yellow
    Write-Host "The scheduled task will fail until you install it: winget install GitHub.cli"
    Write-Host ""
}

# --- Remove existing task if present ---
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Replacing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# --- Create the scheduled task ---

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TriggerScript`"" `
    -WorkingDirectory $ScriptDir

$trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Triggers IPL Fantasy Points scraper GitHub Actions workflow daily at 11:30 PM" | Out-Null

Write-Host ""
Write-Host "Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Schedule:  Daily at $TriggerTime"
Write-Host "  Script:    $TriggerScript"
Write-Host "  User:      $env:USERNAME"
Write-Host ""
Write-Host "Verify with:  Get-ScheduledTask -TaskName '$TaskName' | Format-List"
Write-Host "Test now:     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Remove:       .\setup_scheduled_task.ps1 -Unregister"
