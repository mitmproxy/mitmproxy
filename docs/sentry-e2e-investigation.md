# E2E Sentry Integration Test — Investigation & Fix

## Objective

Verify the full Sentry pipeline after merging the Python addon import mismatch fix:

```
Mac app launch → proxy captures Chrome traffic → oximy_logger emits TRACE events → sentry_service sends to Sentry → events appear in Sentry dashboard
```

## Environment

| Component | Detail |
|-----------|--------|
| macOS app | `Oximy.app` (debug bundle via `make bundle`) |
| Python addon | runs inside `mitmdump` process |
| sentry_sdk | v2.52.0 |
| Sentry project | `macos` (DSN set via `Secrets.swift` → `SENTRY_DSN` env var) |
| Local logs | `~/.oximy/logs/sensor.jsonl`, `~/.oximy/logs/mitmdump.log` |

## Test Plan

Three parallel workstreams:

1. **Build & Launch App** — `make bundle`, copy to `/Applications`, launch
2. **Generate Traffic** — open Chrome to grok.com, generate proxy-captured requests
3. **Poll Sentry API** — query `GET /api/0/projects/oximy/macos/events/` for TRACE events

## Findings

### Initial Observations

| Event Type | Local (`sensor.jsonl`) | Sentry Dashboard |
|------------|----------------------|------------------|
| `CFG.CB.003` (config circuit breaker) | Present | 130+ events found |
| `TRACE.CAPTURE.001` (traffic capture) | 221 events | **0 events** |
| `TRACE.WRITE.001` (trace write) | Present | **0 events** |

Both event types flow through the same code path:
```
oximy_log() → _OximyLogger.emit() → _send_to_sentry() → sentry_service.capture_message()
```

### Key Difference

- **CFG events**: called as `oximy_log(OximyEventCode.CFG_CB_003, "Config circuit breaker CLOSED")` — no `data` parameter, so `extras=None`
- **TRACE events**: called with `data={"host": ..., "method": ..., "path": ...}` — `extras` is always a non-empty dict

## Root Cause

**`sentry_service.py` line 155**: `scope.set_extras(extras)` — this method does **not exist** in `sentry_sdk` v2.

```python
# sentry_service.py — capture_message()
def capture_message(message, level="info", tags=None, extras=None):
    if sdk := _sdk_or_none():
        try:
            with sdk.push_scope() as scope:
                scope.set_level(level)
                if tags:
                    for k, v in tags.items():
                        scope.set_tag(k, v)
                if extras:
                    scope.set_extras(extras)  # <-- AttributeError in sentry_sdk v2
                sdk.capture_message(message)
        except Exception:
            pass  # silently swallows the AttributeError
```

The `except Exception: pass` block (fail-open design) silently caught the `AttributeError`, making the bug completely invisible — no log output, no crash, events just vanished.

### Why CFG Events Worked

CFG events never pass `data`, so `extras` is `None`, and the `if extras:` branch is skipped entirely — bypassing the broken `set_extras()` call.

### Why TRACE Events Failed

TRACE events always pass `data` (host, method, path, status, etc.), so `extras` is always non-None → `set_extras()` is always called → `AttributeError` → caught by `except Exception: pass` → event silently dropped.

## Fix

### `mitmproxy/addons/oximy/sentry_service.py`

Changed `capture_message()` and `capture_exception()` to use the v2-compatible `set_extra()` per-key API:

```python
# BEFORE (broken with sentry_sdk v2):
if extras:
    scope.set_extras(extras)

# AFTER (works with sentry_sdk v2):
if extras:
    for k, v in extras.items():
        scope.set_extra(k, v)
```

Full diff for `capture_message()`:

```diff
 def capture_message(message: str, level: str = "info",
                     tags: dict[str, str] | None = None,
                     extras: dict[str, Any] | None = None) -> None:
     if sdk := _sdk_or_none():
         try:
             with sdk.push_scope() as scope:
                 scope.set_level(level)
                 if tags:
                     for k, v in tags.items():
                         scope.set_tag(k, v)
                 if extras:
-                    scope.set_extras(extras)
+                    for k, v in extras.items():
+                        scope.set_extra(k, v)
                 sdk.capture_message(message)
         except Exception:
             pass
```

Same change applied to `capture_exception()`.

### `mitmproxy/addons/oximy/tests/test_sentry_service.py`

Updated test assertion to match the new per-key API:

```diff
- mock_scope.set_extras.assert_called_once_with({"status": 500})
+ mock_scope.set_extra.assert_called_once_with("status", 500)
```

## Verification

### Tests

```
$ python -m pytest mitmproxy/addons/oximy/tests/ -v --tb=short
474 passed, 0 failed
```

### Live E2E

After deploying the fix to the installed app and generating Chrome traffic to `grok.com`:

| Check | Result |
|-------|--------|
| `sensor.jsonl` has TRACE events | Yes — `TRACE.CAPTURE.001`, `TRACE.WRITE.001` |
| Sentry `macos` project has TRACE events | Yes — 10 events within seconds |
| Event tags correct (`event_code`, `service=trace`) | Yes |
| Event extras present (host, method, path) | Yes |

### Sentry API Confirmation

```
GET /api/0/projects/oximy/macos/events/?sort=-timestamp&per_page=10

Response: 10 events including:
- [TRACE.CAPTURE.001] Captured request trace
- [TRACE.WRITE.001] Wrote trace to disk
Tags: event_code=TRACE.CAPTURE.001, service=trace, operation=capture, component=python
```

## Files Changed

| File | Change |
|------|--------|
| `mitmproxy/addons/oximy/sentry_service.py` | `set_extras()` → `set_extra()` in `capture_message()` and `capture_exception()` |
| `mitmproxy/addons/oximy/tests/test_sentry_service.py` | Updated test assertion for `set_extra` |

## Investigation Process

1. Confirmed sentry_sdk v2.52.0 installed and `SENTRY_DSN` env var set in mitmdump process
2. Verified `sentry_service.initialize()` succeeds (log message: "Sentry initialized for Python addon")
3. Observed CFG events in Sentry but no TRACE events — despite both in local logs
4. Added debug logging to `_send_to_sentry()` and `capture_message()` to trace the call path
5. Debug output confirmed `capture_message()` was being called for TRACE events
6. Added exception logging inside the `except Exception` block
7. Discovered: `'Scope' object has no attribute 'set_extras'`
8. Identified the v1→v2 API break: `scope.set_extras(dict)` → `scope.set_extra(key, value)`
9. Applied fix, removed debug logging, updated tests
10. Verified end-to-end with live traffic

## Lessons Learned

- **Fail-open `except Exception: pass` can hide real bugs** — the `AttributeError` was completely invisible because the exception was swallowed. Consider logging at `debug` level inside catch blocks, even in fail-open designs.
- **sentry_sdk v1 → v2 breaking changes** — `Scope.set_extras()` was removed in v2. The v2 API requires `Scope.set_extra(key, value)` called per key.
- **Test with data-bearing events** — CFG events without `data` passed all manual checks. The bug only manifested with events that included `extras`, which is why TRACE events (always with data) were the ones failing.
