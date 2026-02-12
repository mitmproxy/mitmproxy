# Oximy Sensor — Structured Logging & Sentry Guide

Reference for all structured log events across the Oximy sensor. Use this when implementing logging on new platforms (Windows, Linux) to ensure consistency.

---

## Architecture

```
                          Sentry Dashboard
                    (searchable, alertable, dashboards)
                          |              |
                +---------+              +---------+
                |                                  |
        Desktop App (Swift/.NET)          Python Addon (mitmproxy)
        OximyLogger                       oximy_logger
        (console + JSONL + Sentry)        (console + JSONL + Sentry)
                |                                  |
                v                                  v
        ~/.oximy/logs/app.jsonl           ~/.oximy/logs/sensor.jsonl
```

Both components report to the **same Sentry project**. Events are distinguished by the `component` tag (`swift`/`dotnet` vs `python`). A shared `session_id` (UUID generated on app launch, passed to addon via `OXIMY_SESSION_ID` env var) correlates events across components.

---

## Event Code Format

Every log event has a unique code: **`SVC.OPS.NNN`**

| Segment | Meaning | Examples |
|---------|---------|---------|
| **SVC** | Service area | `APP`, `AUTH`, `MITM`, `HB`, `CFG`, `UPLOAD` |
| **OPS** | Operation type | `INIT`, `FAIL`, `RETRY`, `STATE`, `CB`, `CMD` |
| **NNN** | Numeric ID | `0xx` = lifecycle, `1xx` = state, `2xx` = warning, `3xx` = error, `4xx` = fatal |

---

## Severity Levels

| Level | When to Use | Console Tag | Sentry Action |
|-------|-------------|-------------|---------------|
| `debug` | Per-request decisions, file writes | `[DEBUG]` | Nothing |
| `info` | Service start/stop, successful ops, state transitions | `[INFO] ` | Breadcrumb |
| `warning` | Self-healed errors, retries, circuit breaker trips | `[WARN] ` | Breadcrumb + Sentry event |
| `error` | Failed operation that could not self-heal | `[ERROR]` | Breadcrumb + Sentry event |
| `fatal` | Unrecoverable failure requiring intervention | `[FATAL]` | Breadcrumb + Sentry event |

---

## Action Categories

Each event code maps to an action category telling downstream systems what response is needed:

| Action | Meaning | Expected Response |
|--------|---------|-------------------|
| `none` | Informational | Aggregate for dashboards |
| `monitor` | Track frequency | Alert if threshold exceeded |
| `auto_retry` | System will retry | Alert if retries exhaust |
| `self_healing` | System will self-correct | Verify recovery happened |
| `investigate` | Needs human review | Create investigation ticket |
| `alert_ops` | Alert engineering now | Create high-priority alert |
| `user_action` | End user action needed | Trigger user notification |

---

## Output Formats

### Console (human-readable)

```
[INFO]  MITM.START.002 mitmproxy listening | pid=12345 port=1030
[ERROR] MITM.FAIL.306 mitmproxy process crashed | exit_code=139 pid=12345 signal_name=SIGSEGV
[WARN]  UPLOAD.CB.002 Upload circuit breaker OPEN | cooldown_s=300 failures=3
```

### JSONL File (AI-parseable)

```json
{
  "v": 1,
  "seq": 142,
  "ts": "2026-02-11T19:03:45.123Z",
  "code": "MITM.FAIL.306",
  "level": "error",
  "svc": "mitm",
  "op": "fail",
  "msg": "mitmproxy process crashed",
  "action": "auto_retry",
  "ctx": {
    "component": "swift",
    "session_id": "A1B2C3D4-...",
    "device_id": "AAAA-BBBB",
    "workspace_id": "ws_123",
    "workspace_name": "AcmeCorp"
  },
  "data": {
    "exit_code": 139,
    "signal_name": "SIGSEGV",
    "interpretation": "memory_corruption",
    "pid": 12345,
    "restart_attempt": 2
  },
  "err": {
    "type": "MITMError",
    "code": "MITM_CRASH",
    "message": "Process exited with code 139"
  }
}
```

### Sentry

- **Tags** (searchable): `event_code`, `service`, `operation`, `action_category`, `error_code`
- **Extras** (detail): full `data` dict
- **User context**: `device_id`, `workspace_name`, `workspace_id`, `tenant_id`
- **Breadcrumbs**: auto-created for all `info`+ events
- **Captured events**: created for all `warning`+ events

---

## JSONL Log Rotation

| Setting | Value |
|---------|-------|
| Max file size | 50 MB |
| Rotated files kept | 5 (`sensor.1.jsonl` ... `sensor.5.jsonl`) |
| Total cap per component | ~250 MB |
| Rotation pattern | `app.jsonl` -> `app.1.jsonl` -> `app.2.jsonl` -> ... |

---

## Sentry Scope Tags

These tags are set on the Sentry scope and updated as state changes. Implement all of these in the Windows app:

| Tag | Example Values | Updated When |
|-----|---------------|--------------|
| `device_id` | `"AAAA-BBBB-CCCC"` | On login / app init |
| `workspace_id` | `"ws_abc123"` | On login |
| `workspace_name` | `"Acme Corp"` | On login / heartbeat |
| `tenant_id` | `"tn_xyz"` | On remote state |
| `component` | `"swift"` / `"dotnet"` / `"python"` | On init |
| `app_phase` | `"enrollment"` / `"setup"` / `"ready"` | On phase change |
| `session_id` | `"UUID"` | On app launch |
| `sensor_enabled` | `"true"` / `"false"` | On state change |
| `is_mdm_managed` | `"true"` / `"false"` | On init |
| `proxy_enabled` | `"true"` / `"false"` | On proxy change |
| `proxy_port` | `"1030"` | On proxy enable |
| `mitm_running` | `"true"` / `"false"` | On start / stop |
| `cert_generated` | `"true"` / `"false"` | On cert check |
| `cert_installed` | `"true"` / `"false"` | On cert check |
| `network_connected` | `"true"` / `"false"` | On path update |
| `network_type` | `"Wi-Fi"` / `"Ethernet"` | On path update |

---

## Complete Event Code Registry

### Desktop App Events (Swift / .NET)

Implement these in the desktop app (macOS: Swift, Windows: .NET).

#### App Lifecycle

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `APP.INIT.001` | info | none | Application launched | `app_version`, `build_number`, `macos_version`/`windows_version`, `architecture` | `AppDelegate.applicationDidFinishLaunching` / `App.OnStartup` |
| `APP.STATE.101` | info | none | Setup complete, entering ready phase | _(none)_ | After setup phase completes |
| `APP.START.001` | info | none | Services started | _(none)_ | After all services started |
| `APP.STOP.001` | info | none | App terminating | _(none)_ | `applicationWillTerminate` / `App.OnExit` (BEFORE Sentry flush) |
| `APP.FAIL.301` | error | investigate | Service start failed | `error` | Catch block in `startServices()` |

#### Auth

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `AUTH.AUTH.001` | info | none | User logged in | `workspace`, `has_device_id` | Login success |
| `AUTH.AUTH.002` | info | none | User logged out | _(none)_ | Logout action |
| `AUTH.AUTH.004` | warning | user_action | Credentials cleared due to auth failure | `auth_failure_count` | After clearing credentials on repeated 401s |
| `AUTH.FAIL.201` | warning | auto_retry | API request failed | `method`, `path`, `error` | API client `logFailure()` |
| `AUTH.FAIL.301` | error | user_action | Max auth retries exceeded | `retries` | After exhausting auth retry attempts |
| `AUTH.FAIL.302` | warning | investigate | Auth callback state mismatch | _(none)_ | OAuth callback with wrong state |
| `AUTH.FAIL.303` | warning | investigate | Auth callback missing token | _(none)_ | OAuth callback without token |

#### Enrollment

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `ENROLL.STATE.101` | info | none | Enrollment complete | `workspace`, `device_id` | After device registered + credentials stored |
| `ENROLL.FAIL.301` | error | user_action | Invalid enrollment code | _(none)_ | Invalid code entered |

#### Certificate

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `CERT.STATE.101` | info | none | CA certificate generated | _(none)_ | After cert generation. Also set tag `cert_generated=true` |
| `CERT.STATE.102` | info | none | CA installed to Keychain | `keychain_type` (`"system"` or `"user"`) | After keychain install. Also set tag `cert_installed=true` |
| `CERT.STATE.105` | info | self_healing | CA certificate repaired | _(none)_ | After auto-repair of cert |
| `CERT.CHECK.003` | info | none | Periodic cert health check | _(varies)_ | During heartbeat cycle |
| `CERT.WARN.201` | warning | _(default)_ | System keychain failed, falling back to user keychain | _(none)_ | When system keychain add fails |
| `CERT.FAIL.301` | error | investigate | Certificate generation failed | `error` | Cert generation exception |
| `CERT.FAIL.303` | error | user_action | Keychain add failed | `error` | Keychain trust failure |

#### Proxy

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `PROXY.START.001` | info | none | Proxy enabled | _(none)_ | After system proxy enabled. Also set tags `proxy_enabled=true`, `proxy_port` |
| `PROXY.STOP.001` | info | none | Proxy disabled | _(none)_ | After system proxy disabled. Also set tag `proxy_enabled=false` |
| `PROXY.CLEAN.001` | warning | self_healing | Orphaned proxy cleaned up | `service`, `dead_port` | When cleaning orphaned proxy from previous run |
| `PROXY.STATE.002` | info | none | Pre-existing proxy detected | `host`, `port` | When another proxy is already configured |
| `PROXY.FAIL.301` | error | investigate | Proxy command failed | `error`, `stderr` | When `networksetup`/`netsh` command fails |

#### MITM (mitmproxy process)

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `MITM.START.002` | info | none | mitmproxy listening | `port`, `pid` | After process started and port verified. Also set tags `mitm_running=true`, `mitm_port` |
| `MITM.STOP.001` | info | none | mitmproxy stopped normally | _(none)_ | After clean stop. Also set tag `mitm_running=false` |
| `MITM.FAIL.301` | error | investigate | No available port found | _(none)_ | Port scan returned 0 |
| `MITM.FAIL.304` | error | auto_retry | MITM process start failed | `error` | Process start exception |
| `MITM.FAIL.306` | error | auto_retry | mitmproxy process crashed | `exit_code`, `signal_name`, `interpretation`, `restart_attempt`, `pid` | Process termination handler with non-zero exit. **err**: `(type: "MITMError", code: "MITM_CRASH", message: ...)` |
| `MITM.RETRY.001` | warning | auto_retry | Restart scheduled | `attempt`, `max_attempts`, `delay_ms` | Before scheduling restart |
| `MITM.RETRY.401` | **fatal** | **alert_ops** | Max restart attempts exceeded | `max_attempts`, `restart_count` | When restart count exceeds max |

**Signal interpretation for `MITM.FAIL.306`:**

| Exit Code | Signal | Interpretation |
|-----------|--------|---------------|
| 9, 137 | SIGKILL | `oom_or_force_kill` |
| 11, 139 | SIGSEGV | `memory_corruption` |
| 15, 143 | SIGTERM | `normal_termination` |
| 6, 134 | SIGABRT | `abort` |
| other | SIG{N} | `unknown` |

#### Heartbeat

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `HB.FETCH.001` | info | none | Heartbeat sent | _(none)_ | After successful heartbeat POST |
| `HB.FAIL.201` | warning | monitor | Heartbeat send failed | `error` | Heartbeat POST throws |
| `HB.FAIL.202` | warning | investigate | Unknown command received | `command` | Heartbeat returns unrecognized command |
| `HB.FAIL.203` | warning | monitor | Command failed | `command`, `error` | Command execution exception |
| `HB.STATE.202` | warning | investigate | Workspace ID mismatch | `local_workspace_id`, `server_workspace_id` | Server returns different workspace ID |
| `HB.CMD.002` | info | none | Command executed | `command` | After executing `sync_now`, `restart_proxy`, `disable_proxy` |

#### Network

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `NET.STATE.102` | info | monitor | Connectivity lost | _(none)_ | Network path transitions to unsatisfied. Also set tag `network_connected=false` |
| `NET.STATE.103` | info | none | Connectivity restored | `network_type` | Network path transitions to satisfied. Also set tags `network_connected=true`, `network_type` |
| `NET.STATE.104` | info | none | Interface change | `interfaces` | Network interfaces changed |
| `NET.FAIL.301` | error | _(default)_ | Proxy reconfiguration failed after network change | `error` | Exception during proxy re-enable after network change |

#### Sync

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `SYNC.FAIL.201` | warning | monitor | Sync failed | `error` | Manual sync trigger fails |

#### Remote State

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `STATE.STATE.001` | info | none | Sensor state changed | `sensor_enabled`, `previous` | `sensorEnabled` changes in remote-state.json. Also set tag `sensor_enabled` |
| `STATE.CMD.003` | warning | user_action | Force logout received | _(none)_ | `forceLogout` flag detected in remote state |
| `STATE.FAIL.201` | warning | monitor | Failed to read remote state file | `error` | File read or JSON parse exception |

#### Launch

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `LAUNCH.FAIL.301` | error | investigate | Auto-start registration failed | `error` | LaunchAgent / Task Scheduler registration fails |

#### System Health

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `SYS.HEALTH.001` | info | none | System health snapshot | `mitm_running`, `proxy_enabled`, `sensor_enabled`, `network_connected`, `cert_installed`, `memory_mb`, `uptime_seconds` | Periodic (every 5 min from heartbeat cycle) |

---

### Python Addon Events

These are implemented in the Python addon (`addon.py`, `collector.py`, `normalize.py`, `process.py`). The addon is shared across all platforms — no per-platform changes needed.

#### Config

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `CFG.FETCH.002` | info | none | Config fetched successfully | _(varies)_ | After successful config API response |
| `CFG.FETCH.004` | info | none | Config refreshed | _(varies)_ | After config counts updated |
| `CFG.FAIL.201` | warning | self_healing | Config fetch HTTP error | `status_code` | Non-401 HTTP error from config API |
| `CFG.FAIL.204` | warning | monitor | All config retries failed | _(varies)_ | After exhausting config fetch retries |
| `CFG.FAIL.205` | error | auto_retry | API 401 - invalid token | `consecutive_401_count` | Config fetch returns 401 |
| `CFG.CB.002` | warning | monitor | Config circuit breaker OPEN | `failures`, `cooldown_s` | Config fetch failures hit threshold |
| `CFG.CB.003` | info | none | Config circuit breaker CLOSED | _(none)_ | First success after circuit breaker was open |

#### Upload

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `UPLOAD.STATE.101` | info | none | Batch uploaded | _(varies)_ | After successful trace upload |
| `UPLOAD.FAIL.201` | error | alert_ops | Upload auth failure (401) | _(none)_ | Upload returns 401. **err**: `{type: "HTTPError", code: "UPLOAD_AUTH_401", message: "Device token invalid"}` |
| `UPLOAD.FAIL.203` | warning | auto_retry | Upload retries exhausted | `attempts`, `traces_count` | After exhausting upload retry attempts |
| `UPLOAD.CB.002` | warning | monitor | Upload circuit breaker OPEN | `failures`, `cooldown_s` | Upload failures hit threshold |
| `UPLOAD.CB.003` | info | none | Upload circuit breaker CLOSED | _(none)_ | First success after circuit breaker was open |

#### State

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `STATE.STATE.001` | info | none | Sensor enabled / Sensor disabled | `sensor_enabled` | Sensor state toggled |
| `STATE.CMD.003` | warning | user_action | Force logout triggered from 401 errors | _(none)_ | After 401 threshold triggers force logout |

#### Trace

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `TRACE.FAIL.201` | warning | monitor | Memory buffer full, disk fallback | `buffer_bytes` | Memory buffer exceeds `BUFFER_MAX_BYTES` |

#### Collector (Local Session Upload)

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `COLLECT.FAIL.202` | warning | auto_retry | Local session upload failed | `consecutive_failures`, `buffered_events`, `next_retry_s` / `status` | Upload retries exhausted or 401 auth failure |
| `COLLECT.FAIL.203` | warning | investigate | SQLite DB open/query error | `db`, `error` | SQLite connection or query exception |

#### App Lifecycle (Addon)

| Code | Level | Action | Message | Data Keys | Where to Fire |
|------|-------|--------|---------|-----------|--------------|
| `APP.INIT.001` | info | none | Addon initialized | `whitelist_count`, `blacklist_count`, `passthrough_count`, `device_id`, `fail_open_passthrough` | Addon `running()` hook |
| `APP.STOP.001` | info | none | Addon shutdown | _(none)_ | Addon `done()` hook. Followed by `close_logger()` + `sentry_service.flush()` |

#### Breadcrumbs (no event code, Sentry breadcrumb only)

These are lower-level diagnostic signals — added as Sentry breadcrumbs, not full events.

| Category | Message Pattern | Level | Data Keys | File | Where to Fire |
|----------|----------------|-------|-----------|------|--------------|
| `normalize` | Protobuf decode timed out after {N}s | warning | _(none)_ | `normalize.py` | `TimeoutError` in protobuf decode |
| `normalize` | Protobuf decode failed: {error} | warning | _(none)_ | `normalize.py` | Exception in protobuf decode |
| `normalize` | Protobuf decode setup failed: {error} | warning | _(none)_ | `normalize.py` | Exception creating executor |
| `normalize` | gRPC normalization failed: {error} | warning | _(none)_ | `normalize.py` | Exception in `normalize_grpc()` |
| `normalize` | msgpack decode failed: {type}: {error} | warning | `size` | `normalize.py` | Exception in `_decode_msgpack()` |
| `process` | Process resolution timeout for port {N} | warning | `port`, `timeout_s` | `process.py` | `asyncio.TimeoutError` in process resolution |

---

## Implementation Checklist for Windows (.NET)

### Infrastructure (create these files)

- [ ] **`EventCodes.cs`** — Port the event code enum with `Level`, `Action`, `Service`, `Operation` properties
- [ ] **`OximyLogger.cs`** — Singleton logger: Console + JSONL (`~/.oximy/logs/app.jsonl`) + Sentry
  - Thread-safe (use `lock` for seq counter and file operations)
  - `SessionId` = `Guid.NewGuid().ToString()` on app startup
  - Monotonic `seq` counter for gap detection
  - JSONL rotation at 50 MB, keep 5 rotated files
  - `Close()` method that flushes + closes file handle
- [ ] **Sentry init** — Pass `OXIMY_SESSION_ID` env var to addon process, set `component=dotnet`

### Instrumentation (add log calls at these points)

#### Must-have (critical for diagnosing production issues)

- [ ] `APP.INIT.001` — App startup with version, OS version, architecture, session_id
- [ ] `APP.STOP.001` — App termination (before Sentry flush), then call `OximyLogger.Close()`
- [ ] `AUTH.AUTH.001` — Login success, call `SetFullUserContext()`
- [ ] `AUTH.AUTH.002` — Logout
- [ ] `AUTH.FAIL.301` — Max auth retries exceeded
- [ ] `ENROLL.STATE.101` — Enrollment complete
- [ ] `MITM.START.002` — mitmproxy process started with port + PID, set scope tags
- [ ] `MITM.FAIL.306` — Process crash with exit code + signal interpretation
- [ ] `MITM.RETRY.401` — Max restarts exceeded (fatal)
- [ ] `MITM.RETRY.001` — Restart scheduled with attempt count
- [ ] `STATE.STATE.001` — Sensor enabled/disabled, set `sensor_enabled` tag
- [ ] `STATE.CMD.003` — Force logout received
- [ ] `NET.STATE.102` / `NET.STATE.103` — Connectivity lost/restored, set network tags
- [ ] `PROXY.CLEAN.001` — Orphaned proxy cleanup
- [ ] `HB.FAIL.201` — Heartbeat send failed

#### Nice-to-have (improve diagnosis completeness)

- [ ] `CERT.STATE.101` / `CERT.STATE.102` — Cert generated / installed, set cert tags
- [ ] `CERT.WARN.201` — Keychain/cert-store fallback
- [ ] `PROXY.START.001` / `PROXY.STOP.001` — Proxy enabled/disabled, set proxy tags
- [ ] `HB.STATE.202` — Workspace ID mismatch
- [ ] `HB.CMD.002` — Remote command executed
- [ ] `HB.FAIL.202` — Unknown command
- [ ] `AUTH.FAIL.201` — Individual API request failure
- [ ] `AUTH.AUTH.004` — Credentials cleared
- [ ] `SYNC.FAIL.201` — Sync failure
- [ ] `STATE.FAIL.201` — Remote state file read error
- [ ] `SYS.HEALTH.001` — Periodic health snapshot (every 5 min)
- [ ] `APP.STATE.101` — Phase transition
- [ ] `MITM.FAIL.301` — No available port
- [ ] `MITM.FAIL.304` — Process start failed
- [ ] `NET.FAIL.301` — Proxy reconfiguration failed

### Python Addon (no changes needed)

The addon is shared code. It already has all logging instrumented. Just ensure:

- [ ] `SENTRY_DSN` env var is passed to the addon process (inherited from parent)
- [ ] `OXIMY_SESSION_ID` env var is set before spawning the addon process
- [ ] `sentry-sdk` is included in the embedded Python environment

---

## Sentry SDK Initialization

### Desktop App

```
DSN source: Secrets file or SENTRY_DSN env var
Environment: "production" (release) / "development" (debug)
Sample rate: 1.0 (send ALL events)
Traces sample rate: 0.1 (10% performance traces)
Auto breadcrumbs: enabled
Session tracking: enabled
Send PII: false
Max breadcrumbs: 200
Attach stacktrace: true
```

### Python Addon

```
DSN source: SENTRY_DSN env var (inherited from parent process)
Environment: "production"
Default integrations: disabled (prevents mitmproxy interference)
Auto-enabling integrations: disabled
Sample rate: 1.0
Traces sample rate: 0.0 (no performance tracing)
Send PII: false
Max breadcrumbs: 200
```

---

## Sentry Alert Rules (configure in dashboard)

| Event Code | Rule | Channel |
|------------|------|---------|
| `MITM.RETRY.401` (fatal) | Any occurrence | Slack immediate |
| `UPLOAD.FAIL.201` (401 auth) | >= 3 in 5 minutes | Slack |
| `CFG.CB.002` (circuit breaker) | Open > 15 minutes | Slack |
| `MITM.FAIL.306` (crash) | > 2 in 1 hour per device | Slack |
| Any `fatal` level | Any occurrence | Slack immediate |
| `SYS.HEALTH.001` missing | > 15 min gap per device | Slack (Sentry Cron) |
| `AUTH.FAIL.301` (auth exhausted) | Any occurrence | Slack |

---

## Privacy Safeguards

- Never include raw request/response body bytes in events or breadcrumbs
- Strip `Authorization` header values (replace with `"Bearer ***"`)
- Log device token **presence** (`has_token: true`), never the actual token value
- `sendDefaultPii = false` in both SDK configs
- JSONL files on local disk are acceptable (user's own machine)

---

## Post-Mortem Diagnosis Scenarios

| Scenario | How to Diagnose |
|----------|----------------|
| User couldn't access websites for 30 min | Check `SYS.HEALTH.001` timeline: was `proxy_enabled`? `mitm_running`? Look for `MITM.FAIL.306` crashes, `PROXY.CLEAN.001` orphan cleanup |
| Traces stopped uploading 2 days ago | Search `UPLOAD.FAIL.*` and `UPLOAD.CB.002`. Check when first failure occurred |
| Cert not trusted after install | Check `CERT.STATE.102` `keychain_type` field. Look for `CERT.WARN.201` fallback |
| Proxy broke after OS update | Check `PROXY.FAIL.301` with stderr. Compare OS version in startup snapshot vs previous sessions |
| App crashed and user lost internet | `MITM.FAIL.306` crash event -> `PROXY.CLEAN.001` orphan cleanup on next launch. Timeline shows exact crash + recovery |
| Device stopped reporting | Filter `SYS.HEALTH.001` by device_id. Last health event timestamp = last known alive time |
