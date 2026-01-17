## Project Structure & Deployment
All addon changes should be made in the root `mitmproxy/addons/` directory. This is the source of truth for addon code.

## Building & Bundling for desktop apps
After making changes, you need to build and copy the bundle to the respective platform apps:

### macOS
```bash
cd OximyMac && make build
```
This syncs the addon from `mitmproxy/addons/oximy/` to `OximyMac/Resources/oximy-addon/` (converting imports automatically) and builds the Swift app.

Other useful commands:
- `make sync` - Just sync addon files without building
- `make run` - Sync, build, and run
- `make release` - Build release version
- `make dmg` - Build release DMG for distribution

### Windows
```powershell
cd OximyWindows/scripts && .\build.ps1
```
This copies the addon from `mitmproxy/addons/oximy/` to `OximyWindows/src/OximyWindows/Resources/oximy-addon/`, fixes imports, and builds the .NET app.

Options:
- `.\build.ps1 -Release` - Build release version
- `.\build.ps1 -Clean` - Clean before building
- `.\build.ps1 -CreateInstaller` - Also create installer
- `.\build.ps1 -CreateVelopack -Version "1.0.0"` - Create Velopack release

**Important:** Always make changes in `mitmproxy/addons/oximy/` first, then run the appropriate build command to deploy to platform-specific app bundles. Both build systems automatically sync the addon and fix imports for standalone use.

## CA Certificate
The addon uses its own CA certificate (`oximy-ca-cert.pem`), **not** the default mitmproxy certificate (`mitmproxy-ca-cert.pem`). Both are stored in `~/.mitmproxy/`.

If browsers show certificate errors (e.g., `ERR_CERT_AUTHORITY_INVALID`), install the oximy certificate:

**macOS:**
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/.mitmproxy/oximy-ca-cert.pem
```

**Windows:** Double-click `oximy-ca-cert.pem` and install to "Trusted Root Certification Authorities".

Restart the browser after installation.

## Sensor Configuration (Whitelist/Blacklist)
The addon fetches its filtering configuration from the API, **not** from local files:
- **API endpoint:** `https://api.oximy.com/api/v1/sensor-config`
- **Local cache:** `~/.oximy/sensor-config.json` (fallback only when API is unreachable)

The config includes:
- `whitelistedDomains` - Domains/URLs to capture (supports path patterns)
- `blacklistedWords` - Words to filter out from URLs (e.g., `analytics`, `cspreport`)
- `passthroughDomains` - Domains to skip TLS interception (cert-pinned services)

### Whitelist Pattern Format
The whitelist supports both domain-only and domain+path patterns:

| Pattern | Matches |
|---------|---------|
| `api.openai.com` | Any request to api.openai.com |
| `*.openai.com` | Any request to any openai.com subdomain |
| `gemini.google.com/**/StreamGenerate*` | Only StreamGenerate API calls |
| `api.openai.com/v1/chat/completions` | Only the chat completions endpoint |

Path pattern wildcards:
- `**` - matches any characters including `/` (any path depth)
- `*` - matches any characters except `/` (single path segment)

**To add/remove domains or blacklist words:** Update the API configuration, not the local cache. Local edits will be overwritten on the next config refresh (every 30 minutes or on restart).
