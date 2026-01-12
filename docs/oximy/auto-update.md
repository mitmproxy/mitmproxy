# Auto-Update System

This document describes the automatic update system for Oximy desktop applications.

## Overview

Oximy uses platform-native auto-update frameworks to ensure users always have the latest version:

| Platform | Framework | Update Source |
|----------|-----------|---------------|
| macOS | [Sparkle 2.x](https://sparkle-project.org/) | GitHub Releases appcast.xml |
| Windows | [Velopack](https://velopack.io/) | GitHub Releases API |

## Architecture

### macOS (Sparkle)

Sparkle is the industry-standard update framework for macOS applications.

**Key Components:**
- `UpdateService.swift` - Wraps `SPUStandardUpdaterController`
- `appcast.xml` - XML feed listing available versions
- EdDSA signatures for cryptographic verification

**How It Works:**
1. App starts → waits 5 seconds → checks appcast URL in background
2. Sparkle compares `sparkle:version` in appcast with app's `CFBundleVersion`
3. If update available, shows native macOS update dialog
4. User clicks "Install" → downloads DMG → extracts and replaces app
5. App relaunches with new version

**Configuration (Info.plist):**

| Key | Description | Default |
|-----|-------------|---------|
| `SUFeedURL` | URL to appcast.xml | GitHub Releases |
| `SUPublicEDKey` | Base64 EdDSA public key | Required for verification |
| `SUEnableAutomaticChecks` | Check automatically on launch | `true` |
| `SUScheduledCheckInterval` | Seconds between checks | `86400` (24 hours) |
| `SUAllowsAutomaticUpdates` | Download updates automatically | `true` |

### Windows (Velopack)

Velopack is a modern, Rust-based update framework for .NET applications.

**Key Components:**
- `UpdateService.cs` - Wraps Velopack's `UpdateManager`
- `RELEASES` file - Manifest of available versions
- `.nupkg` files - Delta and full update packages

**How It Works:**
1. App starts → `VelopackApp.Build().Run()` handles update finalization
2. After 5 seconds, `UpdateService.CheckForUpdatesAsync()` queries GitHub
3. If update available, downloads in background with progress reporting
4. User clicks "Install" → app restarts with new version applied

**Configuration:**
- Update source: `GithubSource("https://github.com/OximyHQ/mitmproxy")`
- No token needed for public repositories
- Prerelease updates: disabled by default

## Update Flow

```
┌─────────────────┐
│   App Starts    │
└────────┬────────┘
         │
         ▼ (5 second delay)
┌─────────────────┐
│ Background Check│
└────────┬────────┘
         │
    ┌────┴────┐
    │ Update? │
    └────┬────┘
    No   │   Yes
    │    │    │
    ▼    │    ▼
┌───────┐│┌─────────────────┐
│ Done  │││ Notify User     │
└───────┘│└────────┬────────┘
         │         │
         │         ▼
         │ ┌─────────────────┐
         │ │ User Clicks     │
         │ │ "Install"       │
         │ └────────┬────────┘
         │          │
         │          ▼
         │ ┌─────────────────┐
         │ │ Download Update │
         │ │ (with progress) │
         │ └────────┬────────┘
         │          │
         │          ▼
         │ ┌─────────────────┐
         │ │ Apply & Restart │
         │ └─────────────────┘
         │
         ▼
    ┌─────────────────┐
    │ App Running     │
    │ (Latest Version)│
    └─────────────────┘
```

## Security

### Code Signing

All updates are cryptographically signed:

| Platform | Signing Method |
|----------|----------------|
| macOS | Apple Developer ID + Sparkle EdDSA |
| Windows | (Optional) Authenticode |

### macOS Security Layers

1. **Apple Notarization** - Apple scans app for malware before allowing distribution
2. **Code Signing** - Developer ID certificate verifies authenticity
3. **Sparkle EdDSA** - Cryptographic signature on update archives prevents tampering

### Verification Process

**macOS:**
1. Download DMG from URL in appcast
2. Verify `sparkle:edSignature` matches DMG content
3. Verify code signature matches expected Developer ID
4. If any check fails, update is rejected

**Windows:**
1. Download `.nupkg` from GitHub Releases
2. Velopack verifies package integrity
3. If verification fails, update is rejected

## User Interface

### macOS

Sparkle provides native macOS dialogs:
- "A new version is available" with release notes
- Download progress indicator
- "Restart to Update" button

### Windows

Custom UI in Settings window:
- "Version X.X.X available" status text
- "Check for Updates" / "Download & Install" button
- Progress bar during download

## Manual Update Check

Users can manually trigger an update check:

**macOS:** Settings tab → "Check for Updates" button
**Windows:** Settings window → "Check for Updates" button

## Automatic Updates Toggle

Users can enable/disable automatic update checks:

**macOS:** Settings tab → "Automatic Updates" toggle
**Windows:** (Updates check automatically, no toggle currently)

## Files Reference

### macOS
- `OximyMac/Services/UpdateService.swift` - Update service implementation
- `OximyMac/Views/Tabs/SettingsTab.swift` - UI with update controls
- `OximyMac/Scripts/build-release.sh` - Generates signed DMG and appcast
- `appcast.xml` - Generated during build, uploaded to GitHub Releases

### Windows
- `OximyWindows/src/OximyWindows/Services/UpdateService.cs` - Update service
- `OximyWindows/src/OximyWindows/Views/SettingsWindow.xaml(.cs)` - UI
- `OximyWindows/scripts/build.ps1` - Generates Velopack packages
- `releases/` directory - Contains RELEASES file and .nupkg files

### CI/CD
- `.github/workflows/oximy-release.yml` - Automated release workflow

## Troubleshooting

See [update-troubleshooting.md](./update-troubleshooting.md) for common issues and solutions.
