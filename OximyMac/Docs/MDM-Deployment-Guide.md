# Oximy MDM Deployment Guide

This guide covers enterprise deployment of Oximy via MDM solutions (Jamf, Kandji, Intune, Miradore, SimpleMDM, Mosyle, etc.).

## Prerequisites

- macOS 13.0 (Ventura) or later
- MDM solution with macOS support
- Oximy organization account with device provisioning capabilities
- Signed, notarized PKG installer (`Oximy-X.X.X.pkg`)

## Quick Start

1. **Download PKG** - Get the signed PKG from releases
2. **Create Configuration Profile** - Use the template below
3. **Deploy via MDM** - Upload PKG and profile to your MDM
4. **Assign to Devices** - Target your managed Mac fleet

---

## Deployment Steps

### Step 1: Obtain the PKG Installer

Build the PKG or download from releases:

```bash
# Build locally (requires Xcode and signing certificates)
cd OximyMac
make pkg
```

The PKG installer is located at `OximyMac/build/Oximy-X.X.X.pkg`.

### Step 2: Create Configuration Profile

Create a `.mobileconfig` file with your organization's settings. See the [sample-config.mobileconfig](sample-config.mobileconfig) template.

Key settings to configure:

| Setting | Required | Description |
|---------|----------|-------------|
| `ManagedDeviceToken` | Yes | API token from Oximy dashboard |
| `ManagedWorkspaceId` | Yes | Your organization's workspace ID |
| `ManagedWorkspaceName` | No | Display name (e.g., "Acme Corp") |
| `ManagedSetupComplete` | Yes | Set to `true` to skip all setup UI |

### Step 3: Deploy via MDM

**Jamf Pro:**
1. Upload PKG to Jamf > Computer Management > Packages
2. Create Configuration Profile with the managed preferences
3. Create Policy to install package + apply profile
4. Scope to target computers

**Kandji:**
1. Add Custom App with PKG
2. Create Custom Profile with the configuration
3. Assign to Blueprint

**Intune:**
1. Add macOS LOB app with PKG
2. Create Configuration Profile (Settings Catalog or Custom)
3. Assign to device groups

**SimpleMDM/Mosyle:**
1. Upload PKG as Custom App
2. Create Configuration Profile
3. Deploy to device groups

---

## Configuration Profile Reference

### Domain

```
com.oximy.mac
```

### Managed Preference Keys

#### Credentials (Required for Managed Deployment)

| Key | Type | Description |
|-----|------|-------------|
| `ManagedDeviceToken` | String | Pre-provisioned API authentication token |
| `ManagedDeviceId` | String | Pre-assigned device identifier |
| `ManagedWorkspaceId` | String | Organization/workspace ID |
| `ManagedWorkspaceName` | String | Display name for the workspace |

#### Setup Control

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ManagedSetupComplete` | Boolean | false | Skip all setup UI (enrollment + cert) |
| `ManagedEnrollmentComplete` | Boolean | false | Skip enrollment UI only |
| `ManagedCACertInstalled` | Boolean | false | Indicate CA is pre-installed via MDM |

#### Lockdown Controls

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ForceAutoStart` | Boolean | false | Prevent user from disabling auto-start |
| `DisableUserLogout` | Boolean | false | Hide logout option in UI |
| `DisableQuit` | Boolean | false | Prevent CMD+Q termination |

#### Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `APIEndpoint` | String | (production) | Custom API endpoint URL |
| `HeartbeatInterval` | Integer | 60 | Heartbeat interval in seconds |

---

## CA Certificate Handling

Oximy requires a trusted CA certificate for HTTPS interception. Options:

### Option A: Per-Device CA (Recommended)

Each device generates its own CA certificate. MDM workflow:

1. Deploy PKG (app installs)
2. App generates CA on first launch
3. IT scripts CA trust via MDM post-install or separate script:

```bash
# Trust the device's CA certificate (run as root)
security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.mitmproxy/oximy-ca-cert.pem
```

4. Set `ManagedCACertInstalled=true` in profile after trust is established

### Option B: MDM Script for CA Trust

Deploy a script via MDM to trust the CA after app installation:

```bash
#!/bin/bash
# MDM Script: Trust Oximy CA Certificate

CONSOLE_USER=$(stat -f "%Su" /dev/console)
USER_HOME=$(eval echo ~"$CONSOLE_USER")
CA_CERT="$USER_HOME/.mitmproxy/oximy-ca-cert.pem"

# Wait for app to generate CA (max 60 seconds)
for i in {1..12}; do
    if [ -f "$CA_CERT" ]; then
        break
    fi
    sleep 5
done

if [ -f "$CA_CERT" ]; then
    security add-trusted-cert -d -r trustRoot \
        -k /Library/Keychains/System.keychain \
        "$CA_CERT"
    echo "CA certificate trusted successfully"
else
    echo "CA certificate not found - user may need to launch app first"
    exit 1
fi
```

---

## Data Paths

| Purpose | Path |
|---------|------|
| Device token | `~/.oximy/device-token` |
| CA combined (key+cert) | `~/.mitmproxy/oximy-ca.pem` |
| CA certificate only | `~/.mitmproxy/oximy-ca-cert.pem` |
| Traces/logs | `~/.oximy/traces/`, `~/.oximy/logs/` |
| User LaunchAgent | `~/Library/LaunchAgents/com.oximy.agent.plist` |
| System LaunchAgent | `/Library/LaunchAgents/com.oximy.agent.plist` |

---

## Uninstallation

### Via MDM Script

Deploy the uninstall script to remove Oximy:

```bash
# Standard uninstall (preserves user data)
sudo /Applications/Oximy.app/Contents/Resources/uninstall.sh

# Complete removal including user data
sudo /Applications/Oximy.app/Contents/Resources/uninstall.sh --purge
```

Or use the standalone uninstall script from the PKG:

```bash
sudo /path/to/uninstall.sh --purge
```

### Manual Uninstall Commands

```bash
# Stop app
pkill -x "Oximy"

# Disable proxy
networksetup -setwebproxystate "Wi-Fi" off
networksetup -setsecurewebproxystate "Wi-Fi" off

# Remove LaunchAgents
launchctl unload ~/Library/LaunchAgents/com.oximy.agent.plist
rm ~/Library/LaunchAgents/com.oximy.agent.plist
sudo rm /Library/LaunchAgents/com.oximy.agent.plist

# Remove app
sudo rm -rf /Applications/Oximy.app

# Clear preferences
defaults delete com.oximy.mac

# Remove user data (optional)
rm -rf ~/.oximy
rm ~/.mitmproxy/oximy-*
```

---

## Troubleshooting

### App shows enrollment screen despite configuration

1. Verify configuration profile is installed:
   ```bash
   profiles list | grep oximy
   ```

2. Check managed preferences:
   ```bash
   defaults read com.oximy.mac
   ```

3. Ensure `ManagedDeviceToken` and `ManagedSetupComplete` are set

### Certificate errors in browser

1. Verify CA profile is installed (if using org-level CA)
2. Check System Keychain for "Oximy CA":
   ```bash
   security find-certificate -c "Oximy CA"
   ```
3. Run the CA trust script manually

### App won't start at login

1. Check LaunchAgent exists:
   ```bash
   ls -la /Library/LaunchAgents/com.oximy.agent.plist
   ```

2. Check launchctl status:
   ```bash
   launchctl list | grep oximy
   ```

3. Verify `ForceAutoStart` is set in profile

### Proxy not working

1. Check proxy settings:
   ```bash
   networksetup -getwebproxy "Wi-Fi"
   ```

2. Verify mitmproxy is running:
   ```bash
   ps aux | grep mitmdump
   ```

3. Check app logs:
   ```bash
   tail -f ~/.oximy/logs/*.log
   ```

---

## Support

- Documentation: https://docs.oximy.com
- Support: support@oximy.com
- GitHub: https://github.com/oximyhq/sensor
