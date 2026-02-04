# Issue: Process Resolution Fails on Some macOS Machines

**Status: RESOLVED**

## Problem
The `ProcessResolver` fails to identify client processes (returns `bundle_id=None`) on some macOS machines, causing all whitelisted requests to be rejected by the app origin filter.

**Symptom**: Traces are not being generated even though requests flow through the proxy.

**Affected**: `mitmproxy/addons/oximy/process.py` - `_find_pid_for_port()` method

## Root Cause (Identified)

**Timing issue with lsof queries.**

Even when querying the proxy port (8080), the `request()` hook fires after HTTP data has been received. By then, connections may be in TIME_WAIT state or closing, causing lsof to miss them.

## Solution Implemented

### Strategy: Capture Process at Connection Time

The key insight: the `client_connected()` hook fires when the TCP connection is **definitely active**. We resolve the process there and cache it for later use during `request()`.

### Benefits
- TCP connection guaranteed active at `client_connected` time
- One lsof call per connection (not per request) - better for HTTP/2 and keep-alive
- Existing lsof lookup remains as fallback

### Changes Made (Jan 2026)

**addon.py**:
1. Added `_client_processes: dict[str, ClientProcess]` to cache process by connection ID
2. Added `client_connected()` hook to resolve process at connection time
3. Added `client_disconnected()` hook to clean up mappings
4. Modified `request()` to check cache first, fallback to lsof

```python
async def client_connected(self, client: connection.Client) -> None:
    """Resolve client process at connection time when TCP is definitely active."""
    if not self._enabled or not self._resolver:
        return
    try:
        client_port = client.peername[1]
        client_process = await self._resolver.get_process_for_port(client_port)
        self._client_processes[client.id] = client_process
    except Exception as e:
        logger.debug(f"[CLIENT_CONNECTED] Failed to resolve: {e}")
```

### Debug Logging

Look for these log messages:
- `[CLIENT_CONNECTED] port=XXXXX -> Safari (bundle: com.apple.Safari)` - process captured at connection time
- `[PROCESS] Using cached: Safari (bundle: ...)` - cache hit during request
- `[PROCESS] lsof lookup: ...` - fallback to lsof (cache miss)

## User-Agent Fallback

The User-Agent based fallback in `addon.py` (~line 2357) remains as a safety net:

```python
# Fallback: if bundle_id is None but User-Agent looks like a browser, treat as "host"
if app_type is None and bundle_id is None:
    user_agent = flow.request.headers.get("User-Agent", "").lower()
    if any(browser in user_agent for browser in ("chrome", "firefox", "safari", "edge", "mozilla")):
        app_type = "host"
```

This can be removed once the fix is verified stable in production.

## Affected Machines

| Machine | macOS Version | Status | Notes |
|---------|---------------|--------|-------|
| Hirak's MacBook | ? | Works | Process resolution always worked |
| Naman's MacBook | 26.2 | Fixed | Was failing, now fixed with proxy port strategy |

## Future Improvements (Out of Scope)

For even better reliability, consider:
- Implementing libproc API in mitmproxy_rs (Rust) for zero-subprocess resolution
- Capturing process info at Network Extension layer (OximyMac)
- Migrating Windows from deprecated wmic to PowerShell/Win32 API

## Files Modified

- `mitmproxy/addons/oximy/process.py` - ProcessResolver changes
- `mitmproxy/addons/oximy/addon.py` - Pass proxy_port to ProcessResolver
