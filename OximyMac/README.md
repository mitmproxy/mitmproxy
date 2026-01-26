# OximyMac

macOS app for capturing AI API traffic using mitmproxy.

## Quick Start (Development)

```bash
# Build and run
cd OximyMac
swift build
.build/debug/OximyMac
```

## Project Structure

```
OximyMac/
├── App/                    # App entry point, state, constants
├── Views/                  # SwiftUI views
├── Services/               # Core services (MITM, Proxy, Certificate)
├── Resources/
│   ├── oximy-addon/        # Standalone addon (local imports)
│   └── python-embed/       # Bundled Python + mitmproxy
└── Scripts/
    ├── build-python-embed.sh   # Build standalone Python
    └── build-all.sh            # Build signed release app
```

## Syncing Addon Changes

The addon exists in two places with **different import styles**:

| Location | Import Style | Used By |
|----------|--------------|---------|
| `mitmproxy/addons/oximy/` | Package imports (`from mitmproxy.addons.oximy.bundle`) | Development with system mitmproxy |
| `OximyMac/Resources/oximy-addon/` | Local imports (`from bundle`) | Bundled app |

### After modifying the main addon:

```bash
# 1. Sync files (preserving local import style)
cd /path/to/mitmproxy

# Copy all Python files except __init__.py
for f in mitmproxy/addons/oximy/*.py; do
    [ "$(basename $f)" != "__init__.py" ] && cp "$f" OximyMac/Resources/oximy-addon/
done

# 2. Fix imports in the copied files
cd OximyMac/Resources/oximy-addon

# Replace package imports with local imports
sed -i '' 's/from mitmproxy\.addons\.oximy\./from /g' *.py
sed -i '' 's/from mitmproxy\.addons\.oximy import/from /g' *.py

# 3. Rebuild
cd ..
swift build
```

### One-liner sync script:

```bash
# From mitmproxy root
for f in mitmproxy/addons/oximy/*.py; do [ "$(basename $f)" != "__init__.py" ] && cp "$f" OximyMac/Resources/oximy-addon/; done && sed -i '' 's/from mitmproxy\.addons\.oximy\./from /g' OximyMac/Resources/oximy-addon/*.py && sed -i '' 's/from mitmproxy\.addons\.oximy import/from /g' OximyMac/Resources/oximy-addon/*.py
```

## Building Standalone Python

The app bundles a complete Python environment with mitmproxy. To rebuild:

```bash
# This downloads python-build-standalone and installs mitmproxy
./Scripts/build-python-embed.sh
```

This creates `Resources/python-embed/` (~150MB) containing:
- Standalone Python 3.11
- mitmproxy and all dependencies
- Relocatable wrapper scripts

## Build Commands

| Command | Description |
|---------|-------------|
| `swift build` | Debug build |
| `swift build -c release` | Release build |
| `.build/debug/OximyMac` | Run debug build |
| `./Scripts/build-all.sh` | Build signed .app bundle |

## How It Works

1. **MITMService** starts the bundled mitmproxy on port 1030
2. **ProxyService** configures macOS system proxy to route traffic
3. **CertificateService** manages the Oximy CA certificate
4. **oximy-addon** captures AI traffic and writes to `~/.oximy/traces/`

## Troubleshooting

### mitmproxy not starting
```bash
# Check if port is in use
lsof -i :1030

# Check logs
tail -f ~/.oximy/logs/*.log
```

### Certificate issues
```bash
# Regenerate CA
rm -rf ~/.oximy/oximy-ca*.pem
# Restart app - it will regenerate
```

### Addon import errors
```bash
# Verify local imports in Resources addon
grep "from mitmproxy.addons" OximyMac/Resources/oximy-addon/*.py
# Should return nothing - all imports should be local
```

---

## Known Issues & Fixes (Proxy Startup)

### Issue 1: Corrupted Python C Extension

**Symptoms:**
- App shows "Starting..." but proxy never becomes active
- `~/.oximy/logs/mitmdump.log` shows multiple `MITM STARTED` entries with no output
- Exit code 139 (SIGSEGV) when importing mitmproxy

**Root Cause:** The `_ruamel_yaml_clibz.cpython-312-darwin.so` in build directory gets corrupted during copy.

**Diagnosis:**
```bash
# Hashes should match - if different, file is corrupted
shasum Resources/python-embed/x86_64/lib/python3.12/site-packages/_ruamel_yaml_clibz*
shasum build/Oximy.app/Contents/Resources/python-embed/x86_64/lib/python3.12/site-packages/_ruamel_yaml_clibz*

# Test import directly (should print "OK", not crash)
cd /tmp && PYTHONHOME=".../python-embed/x86_64" \
  PYTHONPATH=".../site-packages" \
  .../bin/python3 -c "from mitmproxy.tools import main; print('OK')"
```

**Fix:** Clean rebuild:
```bash
rm -rf build .build
make bundle
```

---

### Issue 2: Proxy Only Started from UI Event

**Symptoms:**
- Proxy works if you click the menu bar icon
- Proxy never starts if you don't interact with the app
- Only happens when app starts in `.ready` phase (returning user)

**Root Cause:** `MITMService.start()` was only called from `DashboardView.onAppear`. When popover isn't shown, the view never renders.

**Fix:** Added `MITMService.start()` to `AppState.startServices()` with 1-second delay to ensure initialization is complete.

---

### Issue 3: Python Environment Variable Conflict

**Symptoms:**
- Bundled mitmdump works when run from `/tmp`
- Bundled mitmdump crashes when launched by the Swift app
- Works in some directories but not others

**Root Cause:** Swift Process inherits `PYTHONPATH` from parent shell. If developer has local mitmproxy source in path, bundled Python loads wrong code.

**Diagnosis:**
```bash
# Test from clean directory - should work
cd /tmp && /path/to/build/Oximy.app/.../bin/mitmdump --version
```

**Fix:** Clear Python env vars in `MITMService.swift` before launching:
```swift
var env = ProcessInfo.processInfo.environment
env.removeValue(forKey: "PYTHONPATH")
env.removeValue(forKey: "PYTHONHOME")
env.removeValue(forKey: "PYTHONSTARTUP")
env.removeValue(forKey: "VIRTUAL_ENV")
process.environment = env
```

---

---

### Issue 4: Post-install Script Can't Read MDM Preferences (Jamf/MDM Deployments)

**Symptoms:**
- App shows "Starting..." when deployed via Jamf but works locally
- Device token not written to `~/.oximy/device-token`
- System LaunchAgent not created at `/Library/LaunchAgents/com.oximy.agent.plist`

**Root Cause:** The post-install script used `defaults read com.oximy.mac` which reads from `~/Library/Preferences/`. But MDM configuration profiles are deployed to `/Library/Managed Preferences/`, which `defaults read` cannot access without the full path.

**Diagnosis:**
```bash
# This FAILS (returns nothing) - the bug
defaults read com.oximy.mac ManagedDeviceToken

# This WORKS - the fix
defaults read "/Library/Managed Preferences/com.oximy.mac" ManagedDeviceToken
```

**Fix:** Update `Installer/Scripts/postinstall` to read from the managed preferences path:
```bash
# Read from MDM managed preferences first
MDM_TOKEN=$(defaults read "/Library/Managed Preferences/com.oximy.mac" ManagedDeviceToken 2>/dev/null || echo "")

# Fallback to standard defaults (for manual testing)
if [ -z "$MDM_TOKEN" ]; then
    MDM_TOKEN=$(defaults read com.oximy.mac ManagedDeviceToken 2>/dev/null || echo "")
fi
```

Apply the same fix for `ForceAutoStart` and `ManagedCACertInstalled`.

---

### Issue 5: Console User Detection Fails During Headless Jamf Deployment

**Symptoms:**
- Post-install creates files in `/var/root/.oximy/` instead of user's home
- App can't find device token or config files

**Root Cause:** When Jamf deploys with no user logged in, `/dev/console` returns "root" and the script uses `$HOME` which is `/var/root`.

**Fix:** Use multiple detection methods in `postinstall`:
```bash
# Method 1: /dev/console (works when user is logged in)
CONSOLE_USER=$(stat -f "%Su" /dev/console 2>/dev/null)

# Method 2: scutil (more reliable for active sessions)
if [ "$CONSOLE_USER" = "root" ] || [ -z "$CONSOLE_USER" ]; then
    CONSOLE_USER=$(scutil <<< "show State:/Users/ConsoleUser" 2>/dev/null | awk '/Name :/ { print $3 }')
fi

# Method 3: First user in /Users (works for headless)
if [ "$CONSOLE_USER" = "root" ] || [ -z "$CONSOLE_USER" ]; then
    CONSOLE_USER=$(ls -1 /Users 2>/dev/null | grep -v "^Shared$" | grep -v "^Guest$" | head -1)
fi
```

---

### Issue 6: ruamel.yaml C Extension Crashes (SIGSEGV)

**Symptoms:**
- mitmproxy starts then immediately crashes (exit code 139)
- Multiple "MITM STARTED" entries in log with no activity between them
- `proxy_active: false` in `~/.oximy/remote-state.json`
- Crash reports in `~/Library/Logs/DiagnosticReports/python3.12-*.ips`

**Root Cause:** The `ruamel.yaml.clib` C extension crashes on macOS. The Windows build already handles this by installing ruamel.yaml without the C extension, but the Mac build didn't.

**Diagnosis:**
```bash
# Test import - should work, not crash
/Applications/Oximy.app/Contents/Resources/python-embed/bin/python3 -c "import ruamel.yaml"

# Check for crash reports
ls -lt ~/Library/Logs/DiagnosticReports/ | grep python | head -3
```

**Fix (in `Scripts/build-python-embed.sh`):**
```bash
# Pre-install ruamel.yaml WITHOUT the C extension
"$target_dir/bin/pip3" install "ruamel.yaml>=0.18.10,<=0.19.0" --no-binary ruamel.yaml.clib --no-deps

# After installing mitmproxy, remove any C extension that was pulled in
rm -f "$target_dir/lib/python3.12/site-packages/_ruamel_yaml"*.so 2>/dev/null || true
```

**Quick workaround (without rebuilding):**
```bash
# Remove the crashing C extension - ruamel.yaml falls back to pure Python
rm -f /Applications/Oximy.app/Contents/Resources/python-embed/*/lib/python3.12/site-packages/_ruamel_yaml*.so
```

---

### Prevention Checklist

1. **Always clean rebuild** when debugging bundled Python issues
2. **Test from `/tmp`** to isolate environment variable issues
3. **Check both source and build hashes** when .so files misbehave
4. **Proxy starts from `startServices()`** not just UI events (critical for MDM/headless)
5. **MDM preferences are in `/Library/Managed Preferences/`** not standard UserDefaults
6. **Use multiple methods for console user detection** to handle headless deployments
7. **ruamel.yaml C extension must be removed** - use pure Python version only

## Data Locations

| Path | Contents |
|------|----------|
| `~/.oximy/traces/` | Captured AI traffic (JSONL) |
| `~/.oximy/oximy-ca.pem` | CA key + cert (combined) |
| `~/.oximy/oximy-ca-cert.pem` | CA cert only |
