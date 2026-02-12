# Oximy Windows MDM Deployment Guide

This guide covers deploying Oximy to Windows devices using Mobile Device Management (MDM) solutions such as Microsoft Intune, SCCM, or Group Policy.

## Overview

Oximy supports enterprise MDM deployment with the following features:
- **Silent installation** with pre-configured settings
- **Device token provisioning** for automatic enrollment
- **Forced auto-start** that users cannot disable
- **UI lockdown** to prevent logout or quit
- **CA certificate trust** automation

## MDM Configuration Registry Keys

Oximy reads MDM configuration from the Windows Registry at:

```
HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Oximy
```

### Supported Configuration Keys

| Key Name | Type | Description |
|----------|------|-------------|
| `ManagedDeviceToken` | REG_SZ | Pre-provisioned API token for automatic enrollment |
| `ManagedDeviceId` | REG_SZ | Pre-assigned device identifier |
| `ManagedWorkspaceId` | REG_SZ | Organization workspace ID |
| `ManagedWorkspaceName` | REG_SZ | Display name for workspace (shown in UI) |
| `ManagedSetupComplete` | REG_DWORD | Skip all setup UI (1=true, 0=false) |
| `ManagedEnrollmentComplete` | REG_DWORD | Skip enrollment UI only (1=true, 0=false) |
| `ManagedCACertInstalled` | REG_DWORD | CA cert deployed via MDM (1=true, 0=false) |
| `ForceAutoStart` | REG_DWORD | Prevent user from disabling auto-start (1=true) |
| `DisableUserLogout` | REG_DWORD | Hide logout option in UI (1=true) |
| `DisableQuit` | REG_DWORD | Prevent app termination (1=true) |
| `APIEndpoint` | REG_SZ | Custom API URL override |
| `HeartbeatInterval` | REG_DWORD | Heartbeat interval in seconds |

## Microsoft Intune Deployment

### Step 1: Create Configuration Profile

1. In the Intune admin center, go to **Devices > Configuration profiles**
2. Click **Create profile**
3. Select **Platform: Windows 10 and later**
4. Select **Profile type: Settings catalog** (or Custom for OMA-URI)

#### Using Settings Catalog (Recommended)

Create a custom ADMX template or use OMA-URI settings:

```
OMA-URI: ./Device/Vendor/MSFT/Registry/HKLM/SOFTWARE/Policies/Oximy/ManagedDeviceToken
Data type: String
Value: <your-device-token>

OMA-URI: ./Device/Vendor/MSFT/Registry/HKLM/SOFTWARE/Policies/Oximy/ManagedSetupComplete
Data type: Integer
Value: 1

OMA-URI: ./Device/Vendor/MSFT/Registry/HKLM/SOFTWARE/Policies/Oximy/ForceAutoStart
Data type: Integer
Value: 1

OMA-URI: ./Device/Vendor/MSFT/Registry/HKLM/SOFTWARE/Policies/Oximy/DisableUserLogout
Data type: Integer
Value: 1
```

### Step 2: Create App Package

1. Go to **Apps > Windows apps**
2. Click **Add** and select **Windows app (Win32)**
3. Upload `OximySetup-{version}.exe` wrapped as `.intunewin`
4. Configure install command:

```
OximySetup-1.0.0.exe /SILENT /SUPPRESSMSGBOXES /NORESTART
```

5. Configure uninstall command:

```
"%ProgramFiles%\Oximy\unins000.exe" /SILENT
```

6. Set detection rule:
   - Rule type: File
   - Path: `%ProgramFiles%\Oximy`
   - File: `Oximy.exe`
   - Detection method: File or folder exists

### Step 3: Deploy to Device Groups

1. Assign the Configuration Profile to target device groups
2. Assign the App Package to the same groups
3. The configuration profile should be deployed **before** the app installation

## Group Policy Deployment

### Registry Settings via GPO

Create a Group Policy Object with the following registry preferences:

1. Open **Group Policy Management**
2. Create or edit a GPO
3. Navigate to **Computer Configuration > Preferences > Windows Settings > Registry**
4. Add registry items:

| Hive | Key Path | Value Name | Type | Value |
|------|----------|------------|------|-------|
| HKLM | SOFTWARE\Policies\Oximy | ManagedDeviceToken | REG_SZ | `<token>` |
| HKLM | SOFTWARE\Policies\Oximy | ManagedSetupComplete | REG_DWORD | 1 |
| HKLM | SOFTWARE\Policies\Oximy | ForceAutoStart | REG_DWORD | 1 |

### Software Installation via GPO

1. Place the installer on a network share accessible to target machines
2. Create a startup script that runs:

```powershell
# Check if Oximy is already installed
if (-not (Test-Path "$env:ProgramFiles\Oximy\Oximy.exe")) {
    # Run silent install
    Start-Process "\\server\share\OximySetup-1.0.0.exe" -ArgumentList "/SILENT /SUPPRESSMSGBOXES /NORESTART" -Wait
}
```

## PowerShell Deployment Script

For custom deployment scenarios, use this PowerShell script:

```powershell
# Oximy MDM Deployment Script
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceToken,

    [string]$WorkspaceName = "My Organization",
    [string]$InstallerPath = ".\OximySetup-1.0.0.exe",
    [switch]$ForceAutoStart,
    [switch]$DisableLogout,
    [switch]$DisableQuit
)

# Create MDM registry keys
$policyPath = "HKLM:\SOFTWARE\Policies\Oximy"
New-Item -Path $policyPath -Force | Out-Null

# Set configuration values
Set-ItemProperty -Path $policyPath -Name "ManagedDeviceToken" -Value $DeviceToken -Type String
Set-ItemProperty -Path $policyPath -Name "ManagedWorkspaceName" -Value $WorkspaceName -Type String
Set-ItemProperty -Path $policyPath -Name "ManagedSetupComplete" -Type DWord -Value 1

if ($ForceAutoStart) {
    Set-ItemProperty -Path $policyPath -Name "ForceAutoStart" -Type DWord -Value 1
}

if ($DisableLogout) {
    Set-ItemProperty -Path $policyPath -Name "DisableUserLogout" -Type DWord -Value 1
}

if ($DisableQuit) {
    Set-ItemProperty -Path $policyPath -Name "DisableQuit" -Type DWord -Value 1
}

# Install Oximy
Start-Process $InstallerPath -ArgumentList "/SILENT /SUPPRESSMSGBOXES /NORESTART" -Wait

Write-Host "Oximy deployed successfully"
```

## CA Certificate Deployment

### Option 1: Let App Generate Certificate

By default, Oximy generates its CA certificate on first launch. The postinstall script will trust it if `ManagedCACertInstalled=1` is set.

### Option 2: Deploy Certificate via MDM

1. Generate the CA certificate by running Oximy once on a test machine
2. Export from `%USERPROFILE%\.mitmproxy\oximy-ca-cert.pem`
3. Deploy via Intune:
   - Go to **Devices > Configuration profiles**
   - Create a **Trusted certificate** profile
   - Upload the `.pem` file
   - Deploy to Trusted Root store

### Option 3: Deploy via Group Policy

1. Export the certificate to a network share
2. Create a GPO with a startup script:

```powershell
certutil -addstore -f Root "\\server\share\oximy-ca-cert.pem"
```

## Testing MDM Configuration

To test MDM configuration locally before deployment:

```powershell
# Create test MDM configuration
New-Item -Path "HKLM:\SOFTWARE\Policies\Oximy" -Force

Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "ManagedDeviceToken" -Value "test-token-12345"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "ManagedWorkspaceName" -Value "Test Organization"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "ManagedSetupComplete" -Type DWord -Value 1
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "ForceAutoStart" -Type DWord -Value 1
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "DisableUserLogout" -Type DWord -Value 1
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Oximy" -Name "DisableQuit" -Type DWord -Value 1

# Launch Oximy to test
& "$env:ProgramFiles\Oximy\Oximy.exe"
```

To remove test configuration:

```powershell
Remove-Item -Path "HKLM:\SOFTWARE\Policies\Oximy" -Recurse -Force
```

## Verification Checklist

After deployment, verify:

- [ ] App launches directly to Connected phase (skips enrollment)
- [ ] Logout button is hidden in Settings
- [ ] Quit option is hidden/disabled in tray menu and Settings
- [ ] Auto-start toggle is disabled
- [ ] Device token file exists at `%USERPROFILE%\.oximy\device-token`
- [ ] App auto-starts on Windows login
- [ ] Proxy traffic is being captured

## Troubleshooting

### App doesn't skip enrollment

1. Verify registry keys exist at `HKLM\SOFTWARE\Policies\Oximy`
2. Check that `ManagedDeviceToken` is set
3. Check that `ManagedSetupComplete` is set to 1
4. Review app logs at `%USERPROFILE%\.oximy\logs\oximy-debug.log`

### Auto-start not working

1. Check for Scheduled Task at `\Oximy\OximyAutoStart`
2. Verify task is enabled: `schtasks /Query /TN "\Oximy\OximyAutoStart"`
3. Check if `ForceAutoStart` registry key is set

### Certificate errors in browser

1. Verify certificate is in Trusted Root store:
   ```
   certutil -store Root | findstr /i mitmproxy
   ```
2. Restart browser after certificate installation
3. Check that mitmproxy generated the certificate at `%USERPROFILE%\.mitmproxy\oximy-ca-cert.pem`

### User can still quit

1. Verify `DisableQuit` is set to 1 in registry
2. Restart Oximy after changing registry settings
3. MDM configuration is read at app startup

## Uninstallation

### Manual Uninstall

```powershell
# Standard uninstall
& "$env:ProgramFiles\Oximy\unins000.exe" /SILENT

# Remove MDM configuration
Remove-Item -Path "HKLM:\SOFTWARE\Policies\Oximy" -Recurse -Force

# Remove Scheduled Task
schtasks /Delete /TN "\Oximy\OximyAutoStart" /F

# Remove user data (optional)
Remove-Item -Path "$env:USERPROFILE\.oximy" -Recurse -Force
```

### Via MDM

1. Remove app assignment from device groups
2. Remove configuration profile assignment
3. Intune will trigger uninstallation automatically

## Support

For deployment issues:
- Check logs at `%USERPROFILE%\.oximy\logs\oximy-debug.log`
- Contact support at support@oximy.com
- Visit https://oximy.com/support
