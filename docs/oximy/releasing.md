# Releasing a New Version

This guide explains how to release new versions of Oximy for macOS and Windows.

## Prerequisites

Before releasing, ensure you have:

1. **GitHub repository admin access** - Required to trigger workflows and create releases
2. **Secrets configured** - See [secrets-setup.md](./secrets-setup.md)
3. **Version number decided** - Follow semantic versioning (MAJOR.MINOR.PATCH)

## One-Click Release (Recommended)

The easiest way to release is using GitHub Actions:

### Steps

1. Go to the repository on GitHub
2. Click **Actions** tab
3. Select **Oximy Release** workflow from the left sidebar
4. Click **Run workflow** button (top right)
5. Enter the version number (e.g., `1.2.0`)
6. Check "Mark as pre-release" if this is a beta/RC
7. Click **Run workflow**

### What Happens

The workflow automatically:

1. **Builds macOS App**
   - Compiles Swift code
   - Creates app bundle
   - Signs with Developer ID
   - Notarizes with Apple
   - Generates signed DMG
   - Creates appcast.xml for Sparkle

2. **Builds Windows App**
   - Updates version in project files
   - Compiles .NET code
   - Creates Velopack packages (full + delta)
   - Creates Inno Setup installer

3. **Creates GitHub Release**
   - Tags repository as `oximy-vX.X.X`
   - Uploads all artifacts
   - Generates release notes
   - Publishes release

### Duration

Expect the workflow to take approximately:
- macOS build + notarization: ~15-20 minutes
- Windows build: ~5-10 minutes
- Release creation: ~1 minute

Total: **20-30 minutes**

## Manual Release

If you need to build locally (for testing or debugging):

### macOS

```bash
cd OximyMac

# Set required environment variables
export VERSION="1.2.0"
export DEVELOPER_ID="Developer ID Application: Oximy, Inc. (K6H6LCASRA)"
export SPARKLE_PRIVATE_KEY="$(cat ~/.sparkle_private_key)"
export SPARKLE_PUBLIC_KEY="your-base64-public-key"

# Build
./Scripts/build-release.sh

# Output:
# - build/Oximy.app
# - build/Oximy-1.2.0.dmg
# - build/appcast.xml

# Notarize manually (if not using CI)
xcrun notarytool submit build/Oximy-1.2.0.dmg \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "K6H6LCASRA" \
  --wait

xcrun stapler staple build/Oximy-1.2.0.dmg
```

### Windows

```powershell
cd OximyWindows

# Build with Velopack
./scripts/build.ps1 -Release -Clean -CreateVelopack -Version "1.2.0"

# Output:
# - releases/Oximy-1.2.0-full.nupkg
# - releases/RELEASES

# Also create Inno Setup installer (optional)
./scripts/build.ps1 -Release -CreateInstaller
# Output: installer/Output/OximySetup-1.2.0.exe
```

### Upload Manually

```bash
# Create GitHub release
gh release create oximy-v1.2.0 \
  --title "Oximy v1.2.0" \
  --notes "Release notes here" \
  OximyMac/build/Oximy-1.2.0.dmg \
  OximyMac/build/appcast.xml \
  OximyWindows/releases/* \
  OximyWindows/installer/Output/*.exe
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking changes | MAJOR | 1.0.0 → 2.0.0 |
| New features (backward compatible) | MINOR | 1.0.0 → 1.1.0 |
| Bug fixes | PATCH | 1.0.0 → 1.0.1 |

### Pre-release Versions

For beta/RC releases, use pre-release suffix:
- `1.2.0-beta.1`
- `1.2.0-rc.1`

Check "Mark as pre-release" when creating the release.

## Post-Release Checklist

After the release is published:

- [ ] **Verify GitHub Release** - Check all assets were uploaded
- [ ] **Test macOS DMG**
  - Download and mount DMG
  - Drag app to Applications
  - Launch and verify version in Settings
- [ ] **Test Windows installer**
  - Download and run installer
  - Launch and verify version in Settings
- [ ] **Test auto-update**
  - Install previous version
  - Wait for update notification (or click "Check for Updates")
  - Verify update installs successfully
- [ ] **Update changelog/website** (if applicable)
- [ ] **Announce release** (if applicable)

## Troubleshooting

### Workflow fails at notarization

Common causes:
- Invalid Apple credentials
- App not properly signed
- Hardened runtime issues

Check the workflow logs for specific error messages.

### DMG is quarantined

If users see "app is damaged" message:
- Ensure notarization completed successfully
- Verify stapling was done: `xcrun stapler validate Oximy.dmg`

### Velopack packages not detected

Ensure the RELEASES file was generated:
```powershell
Get-Content OximyWindows/releases/RELEASES
```

### Version mismatch

If the app shows wrong version:
- Verify version was updated in all files before build
- Check Info.plist (macOS) or Constants.cs (Windows)

## Rollback

If a release has critical issues:

1. **Delete the release** from GitHub (or mark as pre-release)
2. **Remove the tag**: `git push --delete origin oximy-vX.X.X`
3. **Update appcast.xml** to point to previous version (macOS)
4. Users will automatically get previous version on next update check

## Release Assets Summary

Each release contains:

| File | Platform | Purpose |
|------|----------|---------|
| `Oximy-X.X.X.dmg` | macOS | Installer DMG |
| `appcast.xml` | macOS | Sparkle update feed |
| `Oximy-X.X.X-full.nupkg` | Windows | Velopack full package |
| `Oximy-X.X.X-delta.nupkg` | Windows | Velopack delta update (if applicable) |
| `RELEASES` | Windows | Velopack manifest |
| `OximySetup-X.X.X.exe` | Windows | Inno Setup installer |
