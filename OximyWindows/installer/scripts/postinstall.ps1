# Oximy Windows Post-Install Script
# For MDM deployments, handles device token provisioning, auto-start setup, and CA trust.
# Similar to macOS postinstall script.

param(
    [switch]$Silent,
    [string]$InstallPath = "$env:ProgramFiles\Oximy"
)

$ErrorActionPreference = "Continue"

function Write-Log {
    param([string]$Message)
    if (-not $Silent) {
        Write-Host $Message
    }
}

Write-Log "=== Oximy Post-Install ==="

# Get current user info
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$userProfile = $env:USERPROFILE
Write-Log "User: $currentUser"
Write-Log "Profile: $userProfile"

# Define paths
$oximyDir = Join-Path $userProfile ".oximy"
$tracesDir = Join-Path $oximyDir "traces"
$logsDir = Join-Path $oximyDir "logs"
$cacheDir = Join-Path $oximyDir "cache"
$mitmproxyDir = Join-Path $userProfile ".mitmproxy"

# Create Oximy directories
Write-Log "Creating config directories..."
New-Item -Path $oximyDir -ItemType Directory -Force | Out-Null
New-Item -Path $tracesDir -ItemType Directory -Force | Out-Null
New-Item -Path $logsDir -ItemType Directory -Force | Out-Null
New-Item -Path $cacheDir -ItemType Directory -Force | Out-Null
Write-Log "Directories created at: $oximyDir"

# Read MDM configuration from registry
$policyPath = "HKLM:\SOFTWARE\Policies\Oximy"
$mdmToken = $null
$mdmDeviceId = $null
$mdmWorkspaceId = $null
$mdmWorkspaceName = $null
$forceAutoStart = $false
$mdmCACertInstalled = $false
$mdmSetupComplete = $false

Write-Log "Checking for MDM configuration..."

if (Test-Path $policyPath) {
    Write-Log "MDM configuration found at: $policyPath"

    # Read MDM values
    $mdmToken = (Get-ItemProperty -Path $policyPath -Name "ManagedDeviceToken" -ErrorAction SilentlyContinue).ManagedDeviceToken
    $mdmDeviceId = (Get-ItemProperty -Path $policyPath -Name "ManagedDeviceId" -ErrorAction SilentlyContinue).ManagedDeviceId
    $mdmWorkspaceId = (Get-ItemProperty -Path $policyPath -Name "ManagedWorkspaceId" -ErrorAction SilentlyContinue).ManagedWorkspaceId
    $mdmWorkspaceName = (Get-ItemProperty -Path $policyPath -Name "ManagedWorkspaceName" -ErrorAction SilentlyContinue).ManagedWorkspaceName
    $forceAutoStart = (Get-ItemProperty -Path $policyPath -Name "ForceAutoStart" -ErrorAction SilentlyContinue).ForceAutoStart -eq 1
    $mdmCACertInstalled = (Get-ItemProperty -Path $policyPath -Name "ManagedCACertInstalled" -ErrorAction SilentlyContinue).ManagedCACertInstalled -eq 1
    $mdmSetupComplete = (Get-ItemProperty -Path $policyPath -Name "ManagedSetupComplete" -ErrorAction SilentlyContinue).ManagedSetupComplete -eq 1

    Write-Log "  ManagedDeviceToken: $(if ($mdmToken) { '(set)' } else { '(not set)' })"
    Write-Log "  ManagedDeviceId: $(if ($mdmDeviceId) { $mdmDeviceId } else { '(not set)' })"
    Write-Log "  ManagedWorkspaceName: $(if ($mdmWorkspaceName) { $mdmWorkspaceName } else { '(not set)' })"
    Write-Log "  ForceAutoStart: $forceAutoStart"
    Write-Log "  ManagedCACertInstalled: $mdmCACertInstalled"
    Write-Log "  ManagedSetupComplete: $mdmSetupComplete"
} else {
    Write-Log "No MDM configuration found (standard installation)"
}

# Write device token if MDM provided one
if ($mdmToken) {
    Write-Log "MDM: Writing pre-provisioned device token..."
    $tokenPath = Join-Path $oximyDir "device-token"
    try {
        Set-Content -Path $tokenPath -Value $mdmToken -NoNewline -Force
        Write-Log "Device token written to: $tokenPath"
    } catch {
        Write-Warning "Failed to write device token: $_"
    }
}

# Install system-level Scheduled Task for ForceAutoStart
if ($forceAutoStart) {
    Write-Log "MDM: Installing system Scheduled Task for forced auto-start..."

    $exePath = Join-Path $InstallPath "Oximy.exe"
    $taskName = "Oximy\OximyAutoStart"

    # Remove existing task if present
    schtasks.exe /Delete /TN "$taskName" /F 2>$null

    # Create the scheduled task
    # ONLOGON trigger runs at user logon
    # /RL LIMITED = run with least privileges
    # /DELAY = 30 second delay after logon
    $result = schtasks.exe /Create /F `
        /TN "$taskName" `
        /TR "`"$exePath`"" `
        /SC ONLOGON `
        /RL LIMITED `
        /DELAY 0000:30

    if ($LASTEXITCODE -eq 0) {
        Write-Log "Scheduled Task created successfully"
    } else {
        Write-Warning "Failed to create Scheduled Task (exit code: $LASTEXITCODE)"
    }
}

# Trust CA certificate if MDM says it's been installed
if ($mdmCACertInstalled) {
    $caCertPath = Join-Path $mitmproxyDir "oximy-ca-cert.pem"

    if (Test-Path $caCertPath) {
        Write-Log "MDM: Trusting CA certificate in machine store..."
        try {
            # Add to Trusted Root CA store (requires admin)
            $result = certutil.exe -addstore -f Root "$caCertPath" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "CA certificate trusted successfully"
            } else {
                Write-Warning "certutil returned exit code $LASTEXITCODE"
                Write-Log $result
            }
        } catch {
            Write-Warning "Failed to trust CA certificate: $_"
        }
    } else {
        Write-Log "CA certificate not found at: $caCertPath"
        Write-Log "  (Certificate will be generated on first app launch)"
    }
}

# Register URL scheme if not already registered
Write-Log "Checking URL scheme registration..."
$urlSchemeKey = "HKCU:\Software\Classes\oximy"
if (-not (Test-Path $urlSchemeKey)) {
    try {
        $exePath = Join-Path $InstallPath "Oximy.exe"
        New-Item -Path $urlSchemeKey -Force | Out-Null
        Set-ItemProperty -Path $urlSchemeKey -Name "(Default)" -Value "URL:Oximy Protocol"
        Set-ItemProperty -Path $urlSchemeKey -Name "URL Protocol" -Value ""

        $shellKey = Join-Path $urlSchemeKey "shell\open\command"
        New-Item -Path $shellKey -Force | Out-Null
        Set-ItemProperty -Path $shellKey -Name "(Default)" -Value "`"$exePath`" `"%1`""

        Write-Log "URL scheme registered"
    } catch {
        Write-Warning "Failed to register URL scheme: $_"
    }
} else {
    Write-Log "URL scheme already registered"
}

Write-Log "=== Post-Install Complete ==="
exit 0
