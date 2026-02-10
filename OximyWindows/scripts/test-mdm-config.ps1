# Oximy MDM Configuration Test Script
# Simulates Jamf Pro registry deployment for local testing
#
# Usage:
#   .\test-mdm-config.ps1 -DeviceToken "your-token-here"    # Set MDM config
#   .\test-mdm-config.ps1 -Remove                            # Remove MDM config
#   .\test-mdm-config.ps1 -Status                            # Check current status
#
# Requires: Run as Administrator

param(
    [string]$DeviceToken,
    [string]$WorkspaceName = "Test Workspace",
    [string]$WorkspaceId = "test-workspace-id",
    [string]$DeviceId = "",
    [switch]$SetupComplete,
    [switch]$ForceAutoStart,
    [switch]$DisableLogout,
    [switch]$DisableQuit,
    [switch]$Remove,
    [switch]$Status,
    [switch]$FullLockdown  # Shortcut to enable all lockdown options
)

$ErrorActionPreference = "Stop"
$policyPath = "HKLM:\SOFTWARE\Policies\Oximy"

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Show-Status {
    Write-Host "`n=== Oximy MDM Configuration Status ===" -ForegroundColor Cyan

    if (Test-Path $policyPath) {
        Write-Host "MDM Policy Key: EXISTS" -ForegroundColor Green
        Write-Host ""

        $props = Get-ItemProperty -Path $policyPath -ErrorAction SilentlyContinue

        # Token (masked)
        $token = $props.ManagedDeviceToken
        if ($token) {
            $masked = $token.Substring(0, [Math]::Min(8, $token.Length)) + "..."
            Write-Host "  ManagedDeviceToken:       $masked" -ForegroundColor Green
        } else {
            Write-Host "  ManagedDeviceToken:       (not set)" -ForegroundColor Yellow
        }

        # Other values
        Write-Host "  ManagedWorkspaceName:     $($props.ManagedWorkspaceName ?? '(not set)')"
        Write-Host "  ManagedWorkspaceId:       $($props.ManagedWorkspaceId ?? '(not set)')"
        Write-Host "  ManagedDeviceId:          $($props.ManagedDeviceId ?? '(not set)')"
        Write-Host ""
        Write-Host "  ManagedSetupComplete:     $(if ($props.ManagedSetupComplete -eq 1) { 'YES' } else { 'NO' })"
        Write-Host "  ForceAutoStart:           $(if ($props.ForceAutoStart -eq 1) { 'YES' } else { 'NO' })"
        Write-Host "  DisableUserLogout:        $(if ($props.DisableUserLogout -eq 1) { 'YES' } else { 'NO' })"
        Write-Host "  DisableQuit:              $(if ($props.DisableQuit -eq 1) { 'YES' } else { 'NO' })"
    } else {
        Write-Host "MDM Policy Key: NOT FOUND" -ForegroundColor Yellow
        Write-Host "  (Device is not MDM-managed)"
    }

    # Check device token file
    $tokenFile = Join-Path $env:USERPROFILE ".oximy\device-token"
    Write-Host ""
    if (Test-Path $tokenFile) {
        Write-Host "Device Token File: EXISTS at $tokenFile" -ForegroundColor Green
    } else {
        Write-Host "Device Token File: NOT FOUND" -ForegroundColor Yellow
    }

    # Check Scheduled Task
    $taskExists = schtasks.exe /Query /TN "\Oximy\OximyAutoStart" 2>$null
    Write-Host ""
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Scheduled Task: EXISTS" -ForegroundColor Green
    } else {
        Write-Host "Scheduled Task: NOT FOUND" -ForegroundColor Yellow
    }

    Write-Host ""
}

function Set-MDMConfig {
    Write-Host "`n=== Setting Oximy MDM Configuration ===" -ForegroundColor Cyan

    # Create registry key
    if (-not (Test-Path $policyPath)) {
        New-Item -Path $policyPath -Force | Out-Null
        Write-Host "Created registry key: $policyPath" -ForegroundColor Green
    }

    # Set device token (required)
    if ($DeviceToken) {
        Set-ItemProperty -Path $policyPath -Name "ManagedDeviceToken" -Value $DeviceToken -Type String
        Write-Host "Set ManagedDeviceToken" -ForegroundColor Green
    } else {
        Write-Host "WARNING: No DeviceToken provided. App won't auto-enroll." -ForegroundColor Yellow
    }

    # Set workspace info
    Set-ItemProperty -Path $policyPath -Name "ManagedWorkspaceName" -Value $WorkspaceName -Type String
    Write-Host "Set ManagedWorkspaceName: $WorkspaceName"

    if ($WorkspaceId) {
        Set-ItemProperty -Path $policyPath -Name "ManagedWorkspaceId" -Value $WorkspaceId -Type String
        Write-Host "Set ManagedWorkspaceId: $WorkspaceId"
    }

    if ($DeviceId) {
        Set-ItemProperty -Path $policyPath -Name "ManagedDeviceId" -Value $DeviceId -Type String
        Write-Host "Set ManagedDeviceId: $DeviceId"
    }

    # Handle FullLockdown shortcut
    if ($FullLockdown) {
        $SetupComplete = $true
        $ForceAutoStart = $true
        $DisableLogout = $true
        $DisableQuit = $true
    }

    # Set boolean flags
    $setupValue = if ($SetupComplete -or $DeviceToken) { 1 } else { 0 }
    Set-ItemProperty -Path $policyPath -Name "ManagedSetupComplete" -Value $setupValue -Type DWord
    Write-Host "Set ManagedSetupComplete: $setupValue"

    $autoStartValue = if ($ForceAutoStart) { 1 } else { 0 }
    Set-ItemProperty -Path $policyPath -Name "ForceAutoStart" -Value $autoStartValue -Type DWord
    Write-Host "Set ForceAutoStart: $autoStartValue"

    $logoutValue = if ($DisableLogout) { 1 } else { 0 }
    Set-ItemProperty -Path $policyPath -Name "DisableUserLogout" -Value $logoutValue -Type DWord
    Write-Host "Set DisableUserLogout: $logoutValue"

    $quitValue = if ($DisableQuit) { 1 } else { 0 }
    Set-ItemProperty -Path $policyPath -Name "DisableQuit" -Value $quitValue -Type DWord
    Write-Host "Set DisableQuit: $quitValue"

    Write-Host "`n=== MDM Configuration Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Kill any running Oximy instance"
    Write-Host "  2. Start Oximy fresh to test MDM enrollment"
    Write-Host "  3. Run this script with -Status to verify"
    Write-Host ""
}

function Remove-MDMConfig {
    Write-Host "`n=== Removing Oximy MDM Configuration ===" -ForegroundColor Cyan

    if (Test-Path $policyPath) {
        Remove-Item -Path $policyPath -Recurse -Force
        Write-Host "Removed registry key: $policyPath" -ForegroundColor Green
    } else {
        Write-Host "Registry key not found (already removed)" -ForegroundColor Yellow
    }

    # Optionally remove device token file
    $tokenFile = Join-Path $env:USERPROFILE ".oximy\device-token"
    if (Test-Path $tokenFile) {
        Remove-Item $tokenFile -Force
        Write-Host "Removed device token file" -ForegroundColor Green
    }

    # Remove Scheduled Task if exists
    schtasks.exe /Delete /TN "\Oximy\OximyAutoStart" /F 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Removed Scheduled Task" -ForegroundColor Green
    }

    Write-Host "`n=== MDM Configuration Removed ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Oximy will now behave as a non-managed device." -ForegroundColor Cyan
    Write-Host "Restart Oximy to see the enrollment screen." -ForegroundColor Cyan
    Write-Host ""
}

# Main
if (-not (Test-Administrator)) {
    Write-Host "ERROR: This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

if ($Status) {
    Show-Status
} elseif ($Remove) {
    Remove-MDMConfig
} elseif ($DeviceToken -or $FullLockdown) {
    Set-MDMConfig
} else {
    Write-Host @"

Oximy MDM Configuration Test Script
====================================

Usage:
  # Set MDM config with device token (minimal)
  .\test-mdm-config.ps1 -DeviceToken "your-api-token"

  # Set MDM config with full lockdown
  .\test-mdm-config.ps1 -DeviceToken "your-api-token" -FullLockdown

  # Set MDM config with specific options
  .\test-mdm-config.ps1 -DeviceToken "token" -WorkspaceName "Acme Corp" -ForceAutoStart -DisableLogout

  # Check current MDM status
  .\test-mdm-config.ps1 -Status

  # Remove MDM config (return to normal mode)
  .\test-mdm-config.ps1 -Remove

Options:
  -DeviceToken      API token for device enrollment (required for MDM)
  -WorkspaceName    Organization display name (default: "Test Workspace")
  -WorkspaceId      Workspace ID
  -DeviceId         Device ID
  -SetupComplete    Skip all setup UI
  -ForceAutoStart   Prevent user from disabling auto-start
  -DisableLogout    Hide logout button
  -DisableQuit      Prevent app quit
  -FullLockdown     Enable all lockdown options
  -Status           Show current MDM configuration
  -Remove           Remove all MDM configuration

"@
}
