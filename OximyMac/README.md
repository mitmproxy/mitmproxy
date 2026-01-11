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
rm -rf ~/.oximy/mitmproxy-ca*.pem
# Restart app - it will regenerate
```

### Addon import errors
```bash
# Verify local imports in Resources addon
grep "from mitmproxy.addons" OximyMac/Resources/oximy-addon/*.py
# Should return nothing - all imports should be local
```

## Data Locations

| Path | Contents |
|------|----------|
| `~/.oximy/traces/` | Captured AI traffic (JSONL) |
| `~/.oximy/mitmproxy-ca.pem` | CA key + cert (combined) |
| `~/.oximy/mitmproxy-ca-cert.pem` | CA cert only |
