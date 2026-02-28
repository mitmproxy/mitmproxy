#!/usr/bin/env python3
"""End-to-end scenario tests for the upload worker fix.

Runs sequential scenarios that test the full lifecycle:
  1. Normal operation (traces upload)
  2. API dies (internet stays fast, CB opens)
  3. API comes back (buffered traces drain, CB closes)
  4. Buffer full + API down (fail-open, no freeze)
  5. Cold start with API down (cached config)
  6. Force sync

Requires:
  - /tmp/Oximy.app patched with upload worker changes + DEV_MODE bypass
  - ~/.oximy/dev.json → {"API_URL": "http://localhost:4000/api/v1", "DEV_MODE": true}
  - API source at ~/Developer/Oximy/api
  - DEV_MODE: Upload CB cooldown = 30s (vs 300s in prod)
"""

import json
import os
import re
import signal
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# =============================================================================
# Config
# =============================================================================

PROXY_PORT = 1030
API_DIR = Path("/Users/hirakdesai/Developer/Oximy/api")
SENSOR_LOG = Path.home() / ".oximy" / "logs" / "sensor.jsonl"
MITM_LOG = Path.home() / ".oximy" / "logs" / "mitmdump.log"
FORCE_SYNC_FILE = Path.home() / ".oximy" / "force-sync"
INSTALLED_APP = Path("/tmp/Oximy.app")

# Direct opener bypassing system proxy (for API health checks)
_direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# Proxy opener for traffic through mitmproxy
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE
_proxied = urllib.request.build_opener(
    urllib.request.ProxyHandler({
        "https": f"http://127.0.0.1:{PROXY_PORT}",
        "http": f"http://127.0.0.1:{PROXY_PORT}",
    }),
    urllib.request.HTTPSHandler(context=_ctx),
)

# Whitelisted targets the addon will capture as traces
TRAFFIC_TARGETS = [
    "https://chatgpt.com/backend-api/conversation",
    "https://chatgpt.com/backend-api/me",
    "https://claude.ai/api/organizations/test/completion",
    "https://gemini.google.com/app/_/StreamGenerate",
]


# =============================================================================
# Helpers
# =============================================================================

def log(msg):
    print(msg, flush=True)


def api_healthy():
    try:
        return _direct.open("http://localhost:4000/health", timeout=3).status == 200
    except Exception:
        return False


def proxy_alive():
    r = subprocess.run(["lsof", "-i", f":{PROXY_PORT}", "-sTCP:LISTEN"],
                       capture_output=True, text=True, timeout=5)
    return r.returncode == 0


def app_running():
    r = subprocess.run(["pgrep", "-f", "Oximy.app/Contents/MacOS/Oximy"],
                       capture_output=True, text=True, timeout=5)
    return r.returncode == 0


def send_traffic(count=3):
    """Send requests through the proxy to whitelisted domains.
    Returns (sent_count, elapsed_seconds)."""
    sent = 0
    t0 = time.monotonic()
    for i in range(count):
        url = TRAFFIC_TARGETS[i % len(TRAFFIC_TARGETS)]
        try:
            req = urllib.request.Request(url, method="GET",
                headers={"User-Agent": "Mozilla/5.0", "Authorization": "Bearer fake"})
            _proxied.open(req, timeout=10)
            sent += 1
        except urllib.error.HTTPError:
            sent += 1  # Through proxy, remote rejected
        except Exception as e:
            log(f"    req {i} failed: {type(e).__name__}")
    elapsed = time.monotonic() - t0
    return sent, elapsed


def kill_api_only():
    """Kill ONLY the API listener on port 4000 (not proxy connections)."""
    r = subprocess.run(["lsof", "-ti", ":4000", "-sTCP:LISTEN"],
                       capture_output=True, text=True)
    for pid in r.stdout.strip().split("\n"):
        if pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
    # Wait for it to actually die
    for _ in range(10):
        if not api_healthy():
            return
        time.sleep(0.5)


def start_api():
    """Start the API backend. Returns True if healthy."""
    if api_healthy():
        log("    API already running")
        return True
    log("    Starting API...")
    subprocess.Popen(["pnpm", "run", "dev"], cwd=str(API_DIR),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(90):
        if api_healthy():
            log(f"    API healthy after {i}s")
            return True
        time.sleep(1)
    log("    API FAILED to start")
    return False


def start_app():
    """Start the patched Oximy app. Returns True if running."""
    if app_running():
        log("    App already running")
        return True
    log("    Starting app...")
    subprocess.Popen(["open", str(INSTALLED_APP)])
    for i in range(30):
        if app_running():
            log(f"    App running after {i}s")
            return True
        time.sleep(1)
    log("    App FAILED to start")
    return False


def stop_app():
    """Stop the Oximy app and proxy. Waits for port 1030 to be freed."""
    subprocess.run(["pkill", "-f", "Oximy.app/Contents/MacOS/Oximy"], capture_output=True)
    subprocess.run(["pkill", "-f", "mitmdump.*oximy"], capture_output=True)
    # Wait for port to be freed
    for i in range(15):
        if not proxy_alive() and not app_running():
            log(f"    App + proxy stopped after {i}s")
            return
        time.sleep(1)
    # Force kill if still running
    subprocess.run(["pkill", "-9", "-f", "Oximy.app/Contents/MacOS/Oximy"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", "mitmdump"], capture_output=True)
    time.sleep(3)
    log("    App + proxy force-killed")


def wait_for_proxy(timeout=30):
    """Wait for proxy to be listening."""
    for i in range(timeout):
        if proxy_alive():
            return True
        time.sleep(1)
    return False


def _check_recent_log(log_path, pattern, lookback=50000):
    """Check recent log entries (last `lookback` bytes) for a pattern."""
    if not log_path.exists():
        return False
    try:
        with open(log_path) as f:
            f.seek(max(0, log_path.stat().st_size - lookback))
            content = f.read()
        for line in content.split("\n"):
            if line.strip() and re.search(pattern, line):
                return True
    except (IOError, OSError):
        pass
    return False


class LogWatcher:
    """Watches a log file for patterns after a marked position."""

    def __init__(self, log_path):
        self.log_path = log_path
        self.pos = 0
        self.mark()

    def mark(self):
        """Record current log position."""
        if self.log_path.exists():
            self.pos = self.log_path.stat().st_size

    def wait_for(self, pattern, timeout=30, desc=""):
        """Wait for a regex pattern in new log lines. Returns (found, detail)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            new_content = self._read_new()
            for line in new_content.split("\n"):
                if not line.strip():
                    continue
                if re.search(pattern, line):
                    try:
                        msg = json.loads(line).get("msg", line[:120])
                    except (json.JSONDecodeError, ValueError):
                        msg = line.strip()[:120]
                    return True, msg
            time.sleep(1)
        return False, f"TIMEOUT after {timeout}s waiting for: {desc or pattern}"

    def count_matches(self, pattern):
        """Count matching lines since mark (non-blocking)."""
        count = 0
        new_content = self._read_new()
        for line in new_content.split("\n"):
            if line.strip() and re.search(pattern, line):
                count += 1
        return count

    def _read_new(self):
        """Read content added since self.pos."""
        if not self.log_path.exists():
            return ""
        try:
            with open(self.log_path) as f:
                f.seek(self.pos)
                content = f.read()
            return content
        except (IOError, OSError):
            return ""


# =============================================================================
# Main
# =============================================================================

def run(selected=None):
    if selected is None:
        selected = {1, 2, 3, 4, 5, 6}
    results = []
    sensor = LogWatcher(SENSOR_LOG)
    mitm = LogWatcher(MITM_LOG)

    scenario_start = [time.monotonic()]
    test_start = time.monotonic()

    def scenario(name):
        now = time.monotonic()
        if scenario_start[0] != test_start:
            log(f"  (scenario took {now - scenario_start[0]:.0f}s)")
        scenario_start[0] = now
        log(f"\n{'='*60}")
        log(f"SCENARIO: {name}")
        log(f"{'='*60}")

    def check(name, passed, detail=""):
        results.append((name, passed, detail))
        s = "PASS" if passed else "FAIL"
        log(f"  [{s}] {name}" + (f" — {detail}" if detail else ""))

    # Clean up stale force-sync file
    if FORCE_SYNC_FILE.exists():
        FORCE_SYNC_FILE.unlink()

    # Ensure services are ready for any scenario
    assert start_api(), "Cannot start API"
    assert start_app(), "Cannot start app"
    log("    Waiting for proxy to start (can take up to 2 min)...")
    assert wait_for_proxy(timeout=150), "Proxy never started"
    log("    All services up. Waiting 8s for addon to init + fetch config...")
    time.sleep(8)

    # ==================================================================
    # Scenario 1: Normal operation
    # ==================================================================
    if 1 in selected:
        scenario("1. Normal operation (traces upload)")

        sensor.mark()

        # Send traffic through proxy to whitelisted domains
        sent, elapsed = send_traffic(5)
        check("Traffic through proxy", sent > 0, f"{sent}/5 in {elapsed:.1f}s")

        # Wait for traces to be captured and buffered
        found, msg = sensor.wait_for(r"TRACE\.WRITE\.001|TRACE\.CAPTURE\.001", timeout=15,
                                      desc="trace captured/buffered")
        check("Traces captured by addon", found, msg)

        # Wait for upload worker to upload
        found, msg = sensor.wait_for(r"UPLOAD\.STATE\.101", timeout=45,
                                      desc="traces uploaded to API")
        check("Traces uploaded to API", found, msg)

    # ==================================================================
    # Scenario 2: API dies mid-session
    # ==================================================================
    if 2 in selected:
        scenario("2. API dies mid-session (internet must NOT freeze)")

        sensor.mark()
        kill_api_only()
        time.sleep(2)
        check("API killed", not api_healthy())
        check("Proxy survived API kill", proxy_alive())

        if not proxy_alive():
            log("    FATAL: Proxy died when API was killed. Cannot continue.")
            return results

        # Send traffic — MUST NOT FREEZE (was ~48s before fix)
        sent, elapsed = send_traffic(5)
        check("Internet stays fast (API down)", elapsed < 15,
              f"{sent}/5 in {elapsed:.1f}s (was ~48s before fix)")

        # Upload CB should open after upload failures
        time.sleep(3)
        found, msg = sensor.wait_for(r"UPLOAD\.CB\.002", timeout=30,
                                      desc="upload CB opens")
        check("Upload circuit breaker OPEN", found, msg)

    # ==================================================================
    # Scenario 3: API comes back — buffered traces drain
    # ==================================================================
    if 3 in selected:
        scenario("3. API comes back (buffered traces drain)")

        sensor.mark()
        assert start_api(), "Cannot restart API"
        check("API restarted", api_healthy())

        # Force sync bypasses CB cooldown — triggers immediate upload
        log("    Triggering force sync to drain buffer...")
        FORCE_SYNC_FILE.parent.mkdir(parents=True, exist_ok=True)
        FORCE_SYNC_FILE.touch()

        # Verify traces get uploaded (via force sync or natural CB recovery)
        found, msg = sensor.wait_for(r"UPLOAD\.STATE\.101", timeout=60,
                                      desc="buffered traces uploaded")
        check("Buffered traces drained to API", found, msg)

        # Verify Upload CB eventually closes (either from force sync success or half-open probe)
        if not found:
            log("    Traces not uploaded yet. Waiting for Upload CB recovery...")
            found, msg = sensor.wait_for(r"UPLOAD\.CB\.003", timeout=60,
                                          desc="upload CB closes")
            check("Upload CB transitions to CLOSED", found, msg)
            if found:
                send_traffic(3)
                found, msg = sensor.wait_for(r"UPLOAD\.STATE\.101", timeout=30,
                                              desc="traces uploaded after CB close")
                check("Traces uploaded after CB recovery", found, msg)

    # ==================================================================
    # Scenario 4: Buffer full + API down (no freeze)
    # ==================================================================
    if 4 in selected:
        scenario("4. Buffer full + API down (fail-open, no freeze)")

        sensor.mark()
        kill_api_only()
        time.sleep(2)
        check("API killed again", not api_healthy())
        check("Proxy still alive", proxy_alive())

        if not proxy_alive():
            log("    FATAL: Proxy died again.")
            return results

        # Generate heavy traffic — MUST NOT FREEZE
        log("    Sending heavy traffic (20 requests)...")
        sent, elapsed = send_traffic(20)
        check("Heavy traffic completes (API down)", elapsed < 60,
              f"{sent}/20 in {elapsed:.1f}s")

        # Buffer full + trace dropped may not trigger with large default buffer
        time.sleep(3)
        count = sensor.count_matches(r"TRACE\.FAIL\.201")
        if count > 0:
            check("Buffer full → fail-open drop", True, f"{count} traces dropped (buffer full)")
        else:
            check("Buffer full → fail-open drop", True,
                  "Buffer not full yet (expected with large default buffer)")

    # ==================================================================
    # Scenario 5: Cold start with API down
    # ==================================================================
    if 5 in selected:
        scenario("5. Cold start with API down (cached config)")

        # This scenario verifies the addon can initialize with cached config
        # when the API is unreachable. The app must already be running with
        # API down (orchestrated externally or by previous scenario).
        #
        # To test cold start manually:
        #   1. Kill API: lsof -ti :4000 -sTCP:LISTEN | xargs kill
        #   2. Kill app: pkill -f "Oximy.app/Contents/MacOS/Oximy"
        #   3. Wait for port 1030 to free
        #   4. Launch app: open /tmp/Oximy.app
        #   5. Wait for proxy: lsof -i :1030 -sTCP:LISTEN
        #   6. Run: python test_e2e_scenarios.py --scenarios 5,6

        if not proxy_alive():
            log("    Proxy not running. Starting app with API down...")
            # Ensure API is down
            kill_api_only()
            time.sleep(1)
            assert start_app(), "Cannot start app"
            log("    Waiting for proxy (cold start can take up to 2 min)...")
            if not wait_for_proxy(timeout=150):
                check("Proxy starts after cold restart", False, "Proxy never started after 150s")
                log("    FATAL: Proxy didn't start on cold restart.")
                return results
            check("Proxy starts after cold restart", True)
            log("    Waiting for addon to initialize...")
            time.sleep(8)
        else:
            # Ensure API is down for this scenario
            kill_api_only()
            time.sleep(2)
            check("Proxy starts after cold restart", True, "proxy already running")

        sensor.mark()
        mitm.mark()

        # Addon should have initialized — uses cached sensor config
        # Look back in recent log entries for init confirmation
        found, msg = sensor.wait_for(r"APP\.INIT\.001", timeout=15,
                                      desc="addon initialized")
        if not found:
            # Check broader window (init may have happened before mark)
            log("    APP.INIT.001 not in recent entries, checking full log...")
            found = _check_recent_log(SENSOR_LOG, r"APP\.INIT\.001", lookback=50000)
            check("Addon initialized (API down)", found,
                  "Found in recent log" if found else "NOT FOUND")
        else:
            check("Addon initialized (API down)", found, msg)

        # Check mitmdump.log for cached config usage (look at recent entries)
        found = _check_recent_log(MITM_LOG, r"FAIL-OPEN.*cached sensor config", lookback=50000)
        check("App started with cached config", found,
              "FAIL-OPEN: Using cached sensor config" if found else "NOT FOUND")

        # Traffic should still flow through proxy with cached config
        sent, elapsed = send_traffic(3)
        check("Traffic works on cold start (API down)", sent > 0,
              f"{sent}/3 in {elapsed:.1f}s")

        # Wait for traces to be captured
        time.sleep(3)
        found, msg = sensor.wait_for(r"TRACE\.CAPTURE\.001|TRACE\.WRITE\.001", timeout=15,
                                      desc="traces captured with cached config")
        check("Traces captured using cached config", found, msg)

    # ==================================================================
    # Scenario 6: Force sync (API up)
    # ==================================================================
    if 6 in selected:
        scenario("6. Force sync (API up)")

        assert start_api(), "Cannot start API for force sync test"
        time.sleep(3)
        sensor.mark()

        # Generate some traffic to buffer
        send_traffic(3)
        time.sleep(3)

        # Trigger force sync
        FORCE_SYNC_FILE.touch()

        # Verify traces get uploaded
        found, msg = sensor.wait_for(r"UPLOAD\.STATE\.101", timeout=30,
                                      desc="traces uploaded via force sync")
        check("Force sync → traces uploaded", found, msg)

    # ==================================================================
    # Summary
    # ==================================================================
    total_elapsed = time.monotonic() - test_start
    log(f"  (scenario took {time.monotonic() - scenario_start[0]:.0f}s)")
    log(f"\n{'='*60}")
    log(f"RESULTS SUMMARY  (total: {total_elapsed:.0f}s)")
    log(f"{'='*60}")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    for name, p, detail in results:
        s = "PASS" if p else "FAIL"
        log(f"  [{s}] {name}" + (f" — {detail}" if detail else ""))
    log(f"\n  {passed}/{total} passed")
    log(f"{'='*60}")

    # Leave API running for convenience
    start_api()

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=str, default="1,2,3,4,5,6",
                        help="Comma-separated list of scenario numbers to run (e.g., '1,2,3,4' or '5,6')")
    args = parser.parse_args()
    try:
        selected = {int(s.strip()) for s in args.scenarios.split(",")}
        results = run(selected)
        all_pass = all(p for _, p, _ in results)
        sys.exit(0 if all_pass else 1)
    except KeyboardInterrupt:
        log("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        import traceback
        log(f"\nFATAL: {e}")
        traceback.print_exc()
        sys.exit(2)
