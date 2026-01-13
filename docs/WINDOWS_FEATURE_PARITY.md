# Oximy Windows App - Feature Parity Document

> Generated from analysis of the last 60 GitHub commits involving OximyMac directory.
> Last updated: 2026-01-12

## Executive Summary

This document outlines all features, services, edge cases, and implementation details from the OximyMac application that need to be implemented in the Windows version for feature parity.

---

## Table of Contents

1. [Application Architecture](#1-application-architecture)
2. [Application States & Lifecycle](#2-application-states--lifecycle)
3. [User Interface Components](#3-user-interface-components)
4. [Core Services](#4-core-services)
5. [Python Addon (oximy-addon)](#5-python-addon-oximy-addon)
6. [Data Models](#6-data-models)
7. [API Integration](#7-api-integration)
8. [Configuration & Constants](#8-configuration--constants)
9. [Edge Cases & Error Handling](#9-edge-cases--error-handling)
10. [Windows Implementation Checklist](#10-windows-implementation-checklist)

---

## 1. Application Architecture

### System Tray Application (Windows Equivalent of macOS Menu Bar)

| macOS | Windows Equivalent |
|-------|-------------------|
| Menu Bar Icon (NSStatusItem) | System Tray Icon (NotifyIcon) |
| Popover UI (NSPopover) | Context Window / WPF Popup |
| Activation Policy `.accessory` | Hide from taskbar, tray-only |
| CMD+Q blocking | Override window close behavior |

### Key Architectural Decisions

- **Single Instance**: Prevent multiple app instances
- **Tray-Only Mode**: Application runs hidden, accessible via system tray
- **Popover Window Size**: 340x420 pixels
- **Context Menu**: Right-click on tray icon shows status + quit option
- **Clean Shutdown**: Disable proxy before exit, flush pending events

---

## 2. Application States & Lifecycle

### Three-Phase Application Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Enrollment │ --> │    Setup    │ --> │    Ready    │
│   (Step 1)  │     │   (Step 2)  │     │ (Dashboard) │
└─────────────┘     └─────────────┘     └─────────────┘
```

#### Phase 1: Enrollment
- User enters 6-digit enrollment code
- Device registers with backend API
- Receives device token and workspace info
- Stores credentials locally

#### Phase 2: Setup
- **Step 1**: Certificate installation (CA to Windows Certificate Store)
- **Step 2**: System proxy configuration (WinInet API or netsh)
- Both steps must complete before proceeding

#### Phase 3: Ready (Dashboard)
- Three-tab interface: Home, Settings, Support
- Monitoring toggle (start/stop)
- Device info and sync status display

### Lifecycle Events to Handle

| Event | Action |
|-------|--------|
| App Start | Initialize Sentry, check credentials, restore state |
| First Launch | Auto-show main window |
| Network Change | Reconfigure system proxy |
| mitmproxy Crash | Auto-restart with backoff (max 3 attempts) |
| Auth Failure | After 5 retries, logout and return to enrollment |
| App Quit | Disable proxy, flush pending events, cleanup |

---

## 3. User Interface Components

### 3.1 Enrollment View

**Features:**
- 6-digit code entry with individual text fields
- Visual focus indicator with blinking cursor animation
- Paste support (Ctrl+V filters to 6 digits only)
- Tab/Arrow key navigation between fields
- Auto-advance to next field on digit entry
- Backspace handling (clear current, move to previous)
- Progress indicator: "Step 1 of 2"
- Error message display (fixed-height container to prevent layout shifts)
- "Sign Up" link opens browser to registration page

**API Call:**
```
POST /api/v1/devices/register
Header: X-Enrollment-Token: <6-digit-code>
```

### 3.2 Setup View

**Two Setup Steps:**

1. **Install Certificate**
   - Button: "Install Certificate"
   - Spinner during installation
   - Checkmark when complete
   - Error message if failed

2. **Configure Proxy**
   - Depends on Step 1 completion
   - Button: "Enable Proxy"
   - Spinner during configuration
   - Checkmark when complete

**Additional UI:**
- Progress dots connecting Step 1 and Step 2
- "Skip for Now" / "Set Up Later" option
- "Start Monitoring" button (enabled only when both complete)

### 3.3 Home Tab (Dashboard)

**Connection Status Card:**
- Large status icon (36pt) with color coding:
  - Green: Monitoring Active
  - Gray: Paused/Setup Required
- Status text description
- Port number display when active

**Monitoring Toggle Button:**
- "Start Monitoring" (blue) / "Stop Monitoring" (green)
- Spinner during state change
- Disabled during processing

**Device Info Section:**
- Device name
- Organization/Workspace name
- Events pending count
- Last sync time (relative: "2 hours ago")

### 3.4 Settings Tab

**Sections:**
- Certificate Management (reinstall/remove)
- Proxy Settings (view current config)
- Data Management:
  - Local storage size display
  - "Clear Local Data" button
  - "Browse Traces Folder" button
- Sync Controls:
  - "Sync Now" button
  - Auto-sync status

### 3.5 Support Tab

**Content:**
- Help documentation links
- Email support button
- Terms of Service link
- Privacy Policy link
- App version display

---

## 4. Core Services

### 4.1 MITMService (Proxy Process Management)

**Responsibilities:**
- Locate and launch mitmproxy with bundled Python
- Port discovery and availability checking
- Process monitoring and auto-restart

**Port Selection Algorithm:**
```
1. Try preferred port: 1030 (Oximy founding date reference)
2. Try ports 1031-1130 (above preferred)
3. Try ports 930-1029 (below preferred)
4. Fall back to OS-assigned port (0)
```

**Socket Options:**
- Enable `SO_REUSEADDR` for quick restart (avoids TIME_WAIT)

**Bundled Python Fallback Chain:**
```
1. App bundle's embedded Python
2. Executable-relative Python folder
3. System Python via PATH
4. mitmdump via PATH
```

**Process Arguments:**
```bash
mitmdump \
  -s <addon-path>/addon.py \
  --set oximy_enabled=true \
  --set oximy_output_dir=%USERPROFILE%\.oximy\traces \
  --set confdir=%USERPROFILE%\.oximy \
  --mode regular@<port> \
  --listen-host 127.0.0.1 \
  --ssl-insecure
```

**Auto-Restart Logic:**
```
Max attempts: 3
Backoff delays: 2s, 4s, 8s
Reset counter on successful restart
Send notification after max failures
```

**Observable Properties:**
- `IsRunning: bool`
- `CurrentPort: int?`
- `LastError: string?`
- `RestartCount: int`

### 4.2 ProxyService (System Proxy Configuration)

**Windows Implementation Notes:**

For Windows, use one of these approaches:
1. **WinInet API** (Recommended for programmatic control)
2. **netsh.exe** command-line tool
3. **Registry modification** (requires restart of browsers)

**Required Configurations:**
- HTTP Proxy: 127.0.0.1:<port>
- HTTPS Proxy: 127.0.0.1:<port>
- Bypass list: localhost;127.0.0.1;*.local;169.254/16

**Multi-Interface Support:**
- Windows typically has a single system-wide proxy setting
- May need to handle per-connection settings for VPN scenarios

**Synchronous Disable:**
- Block on app termination to ensure cleanup
- Use synchronous API calls during shutdown

**Observable Properties:**
- `IsProxyEnabled: bool`
- `ConfiguredPort: int?`
- `LastError: string?`

### 4.3 CertificateService (Certificate Management)

**CA Certificate Generation:**
```
Algorithm: RSA 4096-bit
Subject: CN=Oximy CA, O=Oximy Inc, C=US
Validity: 3650 days (10 years)
Output: PEM format (key + cert combined for mitmproxy)
```

**Windows Certificate Store Installation:**

```csharp
// Install to Trusted Root Certification Authorities
X509Store store = new X509Store(StoreName.Root, StoreLocation.LocalMachine);
store.Open(OpenFlags.ReadWrite);
store.Add(certificate);
store.Close();
```

**Alternative: User Certificate Store (no admin required)**
```csharp
StoreLocation.CurrentUser  // Fallback if LocalMachine fails
```

**File Structure (Windows paths):**
```
%USERPROFILE%\.oximy\
├── mitmproxy-ca.pem        (key + cert for mitmproxy)
├── mitmproxy-ca-cert.pem   (cert only for store)
├── mitmproxy-ca.p12        (PKCS12 intermediate)
└── mitmproxy-dhparam.pem   (auto-created by mitmproxy)
```

**File Permissions:**
- Private key: Restrict access to current user only
- Certificate: Readable by all users

**Observable Properties:**
- `IsCAGenerated: bool`
- `IsCAInstalled: bool`
- `LastError: string?`

### 4.4 APIClient (Backend Communication)

**Endpoints:**

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/devices/register` | POST | X-Enrollment-Token header | Device registration |
| `/devices/heartbeat` | POST | Bearer token | Health check |
| `/devices/events` | POST | Bearer token | Event batch upload |

**Device Registration Request:**
```json
{
  "hostname": "DESKTOP-ABC123",
  "displayName": "John's PC",
  "os": "windows",
  "osVersion": "10.0.19045",
  "sensorVersion": "1.0.0",
  "hardwareId": "<GUID from WMI>",
  "ownerEmail": null,
  "permissions": {
    "networkCapture": true,
    "systemExtension": false,
    "fullDiskAccess": false
  }
}
```

**Heartbeat Request:**
```json
{
  "sensorVersion": "1.0.0",
  "uptimeSeconds": 3600,
  "permissions": { ... },
  "metrics": {
    "cpuPercent": 15.5,
    "memoryMb": 2048,
    "eventsQueued": 42
  }
}
```

**Auth Retry Logic:**
```
Max retries on 401: 5
Backoff: 2^attempt seconds
After 5 failures: Clear credentials, return to enrollment
```

**Error Types to Handle:**
| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check for "expired" text |
| 401 | Unauthorized | Retry with backoff |
| 404 | Device Not Found | Re-register |
| 409 | Conflict | Device already registered |
| 429 | Rate Limited | Respect Retry-After header |

### 4.5 HeartbeatService (Periodic Health Checks)

**Configuration:**
- Interval: 60 seconds (configurable via DeviceConfig)
- Runs on background thread/timer

**Metrics Collection (Windows):**
```csharp
// CPU Usage - Use PerformanceCounter or WMI
var cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");

// Memory - Use Process.WorkingSet64 or GC.GetTotalMemory
var memoryMb = Process.GetCurrentProcess().WorkingSet64 / (1024 * 1024);

// Events Queued - Get from SyncService
var eventsQueued = syncService.PendingEventCount;
```

**Server Commands Processing:**
| Command | Action |
|---------|--------|
| `sync_now` | Trigger immediate event sync |
| `restart_proxy` | Restart mitmproxy process |
| `disable_proxy` | Stop proxy without restart |
| `logout` | Clear credentials, return to enrollment |

### 4.6 SyncService (Event Persistence & Upload)

**Sync State Tracking:**
```json
// %USERPROFILE%\.oximy\sync_state.json
{
  "files": {
    "traces_2026-01-12.jsonl": {
      "lastSyncedLine": 150,
      "lastSyncedEventId": "evt_abc123",
      "lastSyncTime": "2026-01-12T10:30:00Z"
    }
  }
}
```

**Sync Configuration:**
- Interval: 5 seconds (configurable)
- Batch size: 100 events (configurable)
- File sorting: By date for chronological upload

**Offline Handling:**
```
On network failure:
  - Set status to "offline"
  - Retry interval: min(60s, flush_interval * failure_count)
  - Events remain local until sync succeeds
```

**App Termination Sync:**
```
- Synchronous flush (blocks up to 5s per batch)
- Best-effort upload of all pending events
- Mark as sent optimistically if timeout
```

**Storage Management Features:**
- Get local storage size (bytes)
- Format human-readable (e.g., "15.3 MB")
- Count trace files
- Clear all data (delete files + reset state)
- Open traces folder in Explorer

**Status Enum:**
- `idle` - Ready for next sync
- `syncing` - Currently uploading
- `synced` - Last sync succeeded
- `offline(retryIn: int)` - Retrying with countdown
- `error(string)` - Last sync failed

### 4.7 NetworkMonitor (Network State Tracking)

**Windows Implementation:**

Use `NetworkChange` class or WMI for network monitoring:

```csharp
NetworkChange.NetworkAddressChanged += OnNetworkChanged;
NetworkChange.NetworkAvailabilityChanged += OnAvailabilityChanged;
```

**Monitored Events:**
- Connection status changes
- Interface list changes
- Interface type changes (Ethernet, Wi-Fi, VPN)

**Debouncing:**
- 1-second debounce to avoid rapid reconfigurations

**On Network Change:**
1. Wait for debounce period
2. Re-enable system proxy with current port
3. Log interface transition

**Observable Properties:**
- `IsConnected: bool`
- `CurrentInterfaces: string[]`
- `LastNetworkChange: DateTime?`

### 4.8 SentryService (Error Tracking)

**Initialization:**
```csharp
SentrySdk.Init(o => {
    o.Dsn = "YOUR_SENTRY_DSN";
    o.Debug = IsDebugBuild;
    o.TracesSampleRate = 0.2;  // 20% sampling in production
    o.Release = $"com.oximy.windows@{version}+{build}";
    o.MaxBreadcrumbs = 100;
    o.AppHangTimeout = TimeSpan.FromSeconds(5);
});
```

**User Context:**
- Anonymous device ID (persistent)
- Username: workspace name
- User ID: device ID

**Context Tags:**
- Windows version
- App version
- Architecture (x64/ARM64)
- App phase
- Proxy status
- Proxy port

**Breadcrumb Types:**
- Navigation (from/to screen)
- User action (action + target)
- State change (category, message, data)
- Error (service, error message)

### 4.9 UpdateService (Automatic Updates)

**Windows Implementation: Velopack**

The macOS app uses Sparkle; for Windows, use Velopack:

```csharp
// Check for updates
var updateManager = new UpdateManager("https://your-update-url");
var updateInfo = await updateManager.CheckForUpdatesAsync();

if (updateInfo != null) {
    await updateManager.DownloadUpdatesAsync(updateInfo);
    updateManager.ApplyUpdatesAndRestart(updateInfo);
}
```

**Update Configuration:**
- Check interval: 24 hours
- Background check on startup (5s delay)
- User-initiated check from Settings

**Observable Properties:**
- `CanCheckForUpdates: bool`
- `IsCheckingForUpdates: bool`
- `UpdateAvailable: bool`
- `LatestVersion: string?`
- `LastUpdateCheckDate: DateTime?`
- `LastError: string?`

---

## 5. Python Addon (oximy-addon)

### Module Structure

```
oximy-addon/
├── __init__.py           # Package initialization
├── addon.py              # Main mitmproxy addon entry point
├── bundle.py             # OISP bundle loading and caching
├── matcher.py            # Traffic classification
├── models.py             # Data structures
├── parser.py             # Request/response parsing
├── writer.py             # JSONL event storage
├── sse.py                # SSE streaming handler
├── passthrough.py        # TLS passthrough rules
├── process.py            # Process attribution
├── investigator.py       # Advanced content analysis
└── investigator_types.py # Investigation data types
```

### Configuration Options

```bash
--set oximy_enabled=true/false          # Enable capture
--set oximy_output_dir=~/.oximy/traces  # Output directory
--set oximy_bundle_url=<url>            # OISP bundle URL
--set oximy_bundle_refresh_hours=24     # Cache refresh interval
--set oximy_include_raw=true/false      # Include raw bodies
```

### Traffic Flow

1. Load OISP bundle (cached with auto-refresh)
2. Classify each request:
   - Domain match
   - App signature match
   - Website pattern match
3. Parse request/response based on API format
4. Extract relevant fields
5. Write normalized event to JSONL

### Supported AI Providers (~60+)

Examples from bundle:
- OpenAI (api.openai.com)
- Anthropic (api.anthropic.com)
- Google AI (generativelanguage.googleapis.com)
- Azure OpenAI (*.openai.azure.com)
- AWS Bedrock (bedrock-runtime.*.amazonaws.com)
- Cohere (api.cohere.ai)
- Mistral (api.mistral.ai)
- And many more...

### Desktop App Signatures (macOS-specific, needs Windows equivalents)

macOS bundle includes process signatures for:
- Cursor (AI code editor)
- Granola (note-taking)
- Comet (AI assistant)
- Raycast (launcher with AI)

**Windows Implementation Needed:**
- Identify equivalent Windows apps
- Match by process name/path
- Add to bundle registry

---

## 6. Data Models

### OximyEvent (Core Event Structure)

```typescript
interface OximyEvent {
  event_id: string;           // UUID
  timestamp: string;          // ISO8601
  source: EventSource;
  trace_level: "full" | "metadata" | "identifiable";
  timing: EventTiming;
  interaction: {
    request: InteractionRequest;
    response: InteractionResponse;
  };
}

interface EventSource {
  type: "api" | "app" | "website";
  id: string;                 // Provider ID
  endpoint: string;           // Full URL
  referer?: string;
  origin?: string;
}

interface EventTiming {
  duration_ms: number;
  ttfb_ms?: number;           // Time to first byte
}

interface InteractionRequest {
  prompt?: string;
  messages?: Message[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  tools?: any[];
  raw?: any;                  // Optional raw body
}

interface InteractionResponse {
  content?: string;
  model?: string;
  finish_reason?: string;
  usage?: TokenUsage;
  raw?: any;                  // Optional raw body
  content_analysis?: any;
}

interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}
```

### SyncState

```typescript
interface SyncState {
  files: Record<string, FileSyncState>;
}

interface FileSyncState {
  lastSyncedLine: number;
  lastSyncedEventId: string;
  lastSyncTime: string;       // ISO8601
}
```

### DeviceConfig (from API)

```typescript
interface DeviceConfig {
  heartbeatIntervalSeconds: number;   // Default: 60
  eventBatchSize: number;             // Default: 100
  eventFlushIntervalSeconds: number;  // Default: 5
  apiEndpoint: string;
}
```

---

## 7. API Integration

### Base URL

Development: `http://localhost:4000/api/v1`
Production: `https://api.oximy.com/api/v1`

### Authentication

- **Enrollment**: `X-Enrollment-Token` header with 6-digit code
- **All other requests**: `Authorization: Bearer <device_token>`

### Request/Response Headers

```http
Content-Type: application/json
Accept: application/json
User-Agent: Oximy-Windows/1.0.0
```

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "The enrollment token is invalid or expired"
  }
}
```

---

## 8. Configuration & Constants

### Directory Structure (Windows)

```
%USERPROFILE%\.oximy\
├── traces\                   # Daily JSONL files
│   └── traces_2026-01-12.jsonl
├── logs\                     # mitmproxy output
│   └── mitmdump.log
├── mitmproxy-ca.pem         # Key + cert combined
├── mitmproxy-ca-cert.pem    # Cert only
├── mitmproxy-ca.p12         # PKCS12 format
├── mitmproxy-dhparam.pem    # DH params
├── bundle_cache.json        # OISP bundle cache
└── sync_state.json          # Sync tracking
```

### Default Values

| Setting | Value | Notes |
|---------|-------|-------|
| MITM Port (preferred) | 1030 | Oximy founding date reference |
| Port Search Range | ±100 | 930-1130 |
| Listen Host | 127.0.0.1 | Localhost only |
| Heartbeat Interval | 60s | Configurable |
| Event Batch Size | 100 | Configurable |
| Event Flush Interval | 5s | Configurable |
| Update Check Interval | 24h | |
| App Hang Timeout | 5s | Sentry tracking |
| Max Breadcrumbs | 100 | Sentry |
| Network Debounce | 1s | |
| Max Restart Attempts | 3 | mitmproxy |
| Restart Backoff | 2s, 4s, 8s | Exponential |
| Max Auth Retries | 5 | |

### Timeouts

| Operation | Timeout |
|-----------|---------|
| API Request | 30s |
| API Resource | 60s |
| App Termination Sync | 5s per batch |
| Sentry Flush | 2s |

---

## 9. Edge Cases & Error Handling

### Must-Handle Scenarios

| Scenario | Handling |
|----------|----------|
| **Port Conflict** | Automatic port discovery with SO_REUSEADDR |
| **Network Change** | Auto-reconfigure proxy, 1s debounce |
| **mitmproxy Crash** | Auto-restart with exponential backoff (max 3) |
| **Auth Failure (401)** | 5-retry with backoff, then logout |
| **Rate Limiting (429)** | Respect Retry-After header |
| **Device Already Registered (409)** | Handle conflict gracefully |
| **Missing Certificate** | Auto-regenerate |
| **Bundle Update Failure** | Continue with cached bundle |
| **Offline Mode** | Queue events locally, retry with backoff |
| **Memory Pressure** | Monitor pending event queue size |
| **Certificate Store Access Denied** | Fallback to user store |
| **Process Termination** | Synchronous cleanup, best-effort sync |

### Cleanup on Shutdown

```
1. Stop network monitor
2. Stop heartbeat timer
3. Stop sync timer
4. Synchronous event flush (max 5s per batch)
5. Disable system proxy (synchronous)
6. Terminate mitmproxy process
7. Flush Sentry events
```

### Graceful Degradation

- **No Certificate**: App runs but no HTTPS interception
- **No System Python**: Use bundled Python
- **No Admin Rights**: Use user certificate store
- **No Network**: Queue events, retry when online

---

## 10. Windows Implementation Checklist

### Critical Components (P0 - Must Have)

- [ ] System tray icon with context menu
- [ ] Three-phase flow (Enrollment → Setup → Ready)
- [ ] 6-digit enrollment code entry UI
- [ ] CA certificate generation (RSA 4096, 10-year validity)
- [ ] Windows Certificate Store installation
- [ ] System proxy configuration (WinInet/netsh)
- [ ] mitmproxy process launch and monitoring
- [ ] Port discovery algorithm
- [ ] JSONL event capture
- [ ] Batch event upload with state tracking
- [ ] Offline queue support
- [ ] API client (register, heartbeat, events)
- [ ] Device metrics collection (CPU, memory)
- [ ] Network change detection
- [ ] Auto-update (Velopack)
- [ ] Error reporting (Sentry)

### Important Features (P1)

- [ ] Multi-interface proxy support
- [ ] mitmproxy auto-restart with backoff
- [ ] Auth retry logic
- [ ] Bundle cache with auto-refresh
- [ ] ~60+ AI provider support
- [ ] SSE streaming response handling
- [ ] Clean shutdown with event flush
- [ ] Browse traces folder

### Nice to Have (P2)

- [ ] Desktop app process attribution
- [ ] Raw body capture option
- [ ] Advanced content analysis
- [ ] Delta updates

### UI Parity

- [ ] Popover-style window
- [ ] Tab-based dashboard
- [ ] Connection status card with color coding
- [ ] Start/Stop monitoring toggle
- [ ] Device info display
- [ ] Events pending counter
- [ ] Last sync timestamp
- [ ] Error message display
- [ ] Progress indicators
- [ ] Enrollment digit entry with paste support

---

## Appendix A: Recent Commit Summary

| Date | Commit | Key Changes |
|------|--------|-------------|
| Jan 11 | d33cd7d | Multi-arch builds, verbose logging, JSONata parsing |
| Jan 11 | aef938f | Configurable parsing, app signatures, bundle loading |
| Jan 11 | df246b1 | Bundle cache expiry mechanism, proxy bypass |
| Jan 11 | b2baa75 | Periodic bundle refresh, force refresh option |
| Jan 11 | 5314cc0 | Workspace name updates, local data management |
| Jan 11 | 365a2bb | Auto-update via Sparkle, UpdateService |
| Jan 11 | 56c1c4e | First launch auto-show, DMG improvements |
| Jan 11 | 4fb8f06 | SyncService, HeartbeatService, APIClient, EnrollmentView |
| Jan 10 | e302e6a | Sentry integration, tabbed UI, comprehensive refactor |
| Jan 10 | 1c9ae2c | Process attribution for network connections |
| Jan 9 | e68eb26 | Initial OximyMac project setup |

---

## Appendix B: Technology Stack Comparison

| Component | macOS | Windows Equivalent |
|-----------|-------|-------------------|
| UI Framework | SwiftUI | WPF / WinUI 3 / Avalonia |
| Tray Icon | NSStatusItem | NotifyIcon / H.NotifyIcon |
| Popover | NSPopover | Popup / Custom Window |
| Certificate Store | Keychain | Windows Certificate Store |
| Proxy Config | networksetup | WinInet API / netsh |
| Updates | Sparkle | Velopack |
| Crash Reporting | Sentry-Cocoa | Sentry.NET |
| Network Monitor | NWPathMonitor | NetworkChange |
| Process Info | NSRunningApplication | Process / WMI |
| Metrics | Mach APIs | PerformanceCounter / WMI |

---

*Document generated from OximyMac codebase analysis. For questions, contact the development team.*
