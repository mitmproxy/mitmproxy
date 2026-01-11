# Auto-Update Troubleshooting

This guide helps diagnose and fix common issues with the Oximy auto-update system.

## macOS Issues

### "Update check failed"

**Symptoms:** Clicking "Check for Updates" shows an error or nothing happens.

**Possible Causes & Solutions:**

1. **No internet connection**
   - Check your network connection
   - Try opening https://github.com in a browser

2. **Incorrect appcast URL**
   - Verify `SUFeedURL` in Info.plist points to:
     `https://github.com/OximyHQ/mitmproxy/releases/latest/download/appcast.xml`
   - Test the URL in a browser - it should return XML

3. **Firewall blocking**
   - Check if a firewall is blocking outgoing connections
   - Allow Oximy in System Settings → Privacy & Security → Firewall

4. **DNS issues**
   - Try flushing DNS cache: `sudo dscacheutil -flushcache`

**Debug:**
```bash
# Check Sparkle logs
log show --predicate 'subsystem == "org.sparkle-project.Sparkle"' --last 1h

# Test appcast URL
curl -I https://github.com/OximyHQ/mitmproxy/releases/latest/download/appcast.xml
```

### "Signature verification failed"

**Symptoms:** Update downloads but fails to install with signature error.

**Possible Causes & Solutions:**

1. **Wrong public key**
   - The `SUPublicEDKey` in Info.plist doesn't match the private key used to sign the DMG
   - This requires a new app build with the correct public key

2. **Corrupted download**
   - Delete `~/Library/Caches/com.oximy.mac/` and try again
   - Check available disk space

3. **Tampered DMG**
   - Download the DMG manually from GitHub Releases
   - Compare checksums

**Debug:**
```bash
# Verify DMG signature manually
.build/checkouts/Sparkle/bin/sign_update --verify Oximy.dmg
```

### "The update was not properly signed"

**Symptoms:** macOS Gatekeeper blocks the updated app.

**Possible Causes & Solutions:**

1. **App not notarized**
   - Check notarization status:
     ```bash
     spctl -a -v /Applications/Oximy.app
     ```
   - If it shows "rejected", the app needs notarization

2. **Notarization not stapled**
   - Verify DMG has ticket:
     ```bash
     xcrun stapler validate /path/to/Oximy.dmg
     ```

3. **Code signature invalid**
   - Check signature:
     ```bash
     codesign -dvv /Applications/Oximy.app
     ```

### Update dialog doesn't appear

**Symptoms:** No update notification even when a new version exists.

**Possible Causes & Solutions:**

1. **Automatic checks disabled**
   - Go to Settings → Check if "Automatic Updates" is enabled

2. **Already checked recently**
   - Sparkle has a minimum check interval (default 24 hours)
   - Click "Check for Updates" manually to force a check

3. **App version is current**
   - Verify your version in Settings
   - Check the latest version on GitHub Releases

4. **First launch behavior**
   - Sparkle skips update check on first launch by design
   - The check happens on subsequent launches

**Debug:**
```bash
# Check last update check date
defaults read com.oximy.mac SULastCheckTime
```

### App crashes during update

**Symptoms:** App crashes or freezes when applying update.

**Possible Causes & Solutions:**

1. **Insufficient permissions**
   - Make sure you have write access to /Applications
   - Try running from ~/Applications instead

2. **Disk full**
   - Check available disk space
   - Need at least 500MB free

3. **App in use**
   - Close all Oximy-related processes
   - Check Activity Monitor for any Oximy processes

## Windows Issues

### "Failed to check for updates"

**Symptoms:** Update check fails with network error.

**Possible Causes & Solutions:**

1. **No internet connection**
   - Check network connectivity
   - Try opening https://github.com in a browser

2. **GitHub API rate limited**
   - Wait a few minutes and try again
   - Authenticated requests have higher limits

3. **Firewall/antivirus blocking**
   - Add Oximy to firewall exceptions
   - Temporarily disable antivirus to test

**Debug:**
```powershell
# Test GitHub API access
Invoke-RestMethod "https://api.github.com/repos/OximyHQ/mitmproxy/releases/latest"
```

### "Update download failed"

**Symptoms:** Download starts but fails to complete.

**Possible Causes & Solutions:**

1. **Insufficient disk space**
   - Check available space on C: drive
   - Need at least 500MB free

2. **Network interruption**
   - Try again with stable connection
   - Use wired connection if possible

3. **Corrupted partial download**
   - Delete Velopack cache:
     ```
     %TEMP%\Velopack\
     ```
   - Try again

### App doesn't restart after update

**Symptoms:** Update completes but app doesn't restart.

**Possible Causes & Solutions:**

1. **Velopack not initialized**
   - Ensure `VelopackApp.Build().Run()` is called first in `App.OnStartup`
   - Check that it's before any other code

2. **Antivirus blocking**
   - Some antivirus software blocks app restarts
   - Add Oximy to exclusions

3. **Process still running**
   - Check Task Manager for OximyWindows.exe
   - End task and start app manually

### "Access denied" during update

**Symptoms:** Update fails with permission error.

**Possible Causes & Solutions:**

1. **App installed in protected location**
   - Default install is in `C:\Program Files\Oximy`
   - This requires admin rights for updates
   - Run app as administrator once

2. **File locked by another process**
   - Close all Oximy windows
   - Check for any plugins/extensions using Oximy

3. **Windows Defender blocking**
   - Add Oximy folder to exclusions

**Debug:**
```powershell
# Check file permissions
icacls "C:\Program Files\Oximy"
```

### Update UI not showing progress

**Symptoms:** Progress bar stays at 0% or doesn't appear.

**Possible Causes & Solutions:**

1. **UI not bound to UpdateService**
   - Check Settings window is subscribing to PropertyChanged events
   - Verify UpdateProgressBar visibility is set correctly

2. **Download too fast**
   - On fast connections, progress may jump from 0 to 100
   - This is normal behavior

## Logs Location

### macOS

```bash
# Sparkle logs (Console.app or terminal)
log show --predicate 'subsystem == "org.sparkle-project.Sparkle"' --last 1h

# App logs
ls ~/Library/Logs/Oximy/

# Sparkle preferences
defaults read com.oximy.mac | grep -i sparkle
```

### Windows

```
# App logs
%LOCALAPPDATA%\Oximy\logs\

# Velopack cache
%TEMP%\Velopack\

# Event Viewer
eventvwr.msc → Windows Logs → Application
```

## Testing Updates Locally

### macOS Local Test

1. Build an older version (e.g., 0.9.0):
   ```bash
   VERSION=0.9.0 ./Scripts/build-release.sh
   ```

2. Install it:
   ```bash
   open build/Oximy-0.9.0.dmg
   # Drag to Applications
   ```

3. Build a newer version (e.g., 1.0.0):
   ```bash
   VERSION=1.0.0 ./Scripts/build-release.sh
   ```

4. Create local appcast pointing to the new DMG:
   ```xml
   <!-- Edit build/appcast.xml -->
   <enclosure url="file:///path/to/build/Oximy-1.0.0.dmg" .../>
   ```

5. Point app to local appcast:
   ```bash
   defaults write com.oximy.mac SUFeedURL "file:///path/to/build/appcast.xml"
   ```

6. Launch old version → Check for Updates

7. Reset when done:
   ```bash
   defaults delete com.oximy.mac SUFeedURL
   ```

### Windows Local Test

1. Build v1.0.0:
   ```powershell
   ./scripts/build.ps1 -Release -CreateVelopack -Version "1.0.0"
   ```

2. Install from `releases/` folder

3. Build v1.0.1:
   ```powershell
   ./scripts/build.ps1 -Release -CreateVelopack -Version "1.0.1"
   ```

4. Start local HTTP server:
   ```powershell
   cd releases
   python -m http.server 8080
   ```

5. Temporarily modify UpdateService.cs:
   ```csharp
   var source = new SimpleWebSource("http://localhost:8080");
   ```

6. Launch v1.0.0 → Check for Updates

7. Revert code changes when done

## Common Error Messages

| Error | Platform | Meaning | Solution |
|-------|----------|---------|----------|
| "appcast file not found" | macOS | Appcast URL returned 404 | Verify SUFeedURL, check GitHub Release has appcast.xml |
| "signature verification failed" | macOS | EdDSA signature mismatch | Check SUPublicEDKey matches signing key |
| "damaged and can't be opened" | macOS | Gatekeeper block | App needs notarization |
| "update check timeout" | Both | Network timeout | Check connection, try again |
| "insufficient disk space" | Both | Not enough free space | Free up disk space |
| "access denied" | Windows | Permission issue | Run as admin or check folder permissions |

## Getting Help

If you're still having issues:

1. **Check the logs** using the commands above
2. **Search existing issues** on GitHub
3. **Create a new issue** with:
   - Oximy version
   - OS version
   - Error message
   - Relevant log output
