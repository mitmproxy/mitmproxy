"""
Oximy addon for mitmproxy.

Captures AI API traffic with whitelist/blacklist filtering.
Supports: HTTP/REST, SSE, WebSocket, HTTP/2, HTTP/3, gRPC

Pipeline: Passthrough → Whitelist → Blacklist → Capture to JSONL
"""

from __future__ import annotations

import atexit
import fnmatch
import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import IO

from mitmproxy import ctx, http, tls

# Import ProcessResolver - handle both package and script modes
try:
    from .process import ClientProcess, ProcessResolver
except ImportError:
    from process import ClientProcess, ProcessResolver

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

PROXY_HOST = "127.0.0.1"
PROXY_PORT = "8080"
NETWORK_SERVICE = "Wi-Fi"


# =============================================================================
# SYSTEM PROXY
# =============================================================================

def _set_system_proxy(enable: bool) -> None:
    """Enable or disable system proxy settings (cross-platform)."""
    if sys.platform == "darwin":
        _set_macos_proxy(enable)
    elif sys.platform == "win32":
        _set_windows_proxy(enable)


def _set_windows_proxy(enable: bool) -> None:
    """Enable or disable Windows system proxy via registry."""
    proxy_server = f"{PROXY_HOST}:{PROXY_PORT}"
    reg_path = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    try:
        if enable:
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "1", "/f"],
                           check=True, capture_output=True)
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyServer", "/t", "REG_SZ", "/d", proxy_server, "/f"],
                           check=True, capture_output=True)
            logger.info(f"Windows proxy enabled: {proxy_server}")
        else:
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "0", "/f"],
                           check=True, capture_output=True)
            logger.info("Windows proxy disabled")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to set Windows proxy: {e}")


def _set_macos_proxy(enable: bool) -> None:
    """Enable or disable macOS system proxy."""
    try:
        if enable:
            subprocess.run(["networksetup", "-setsecurewebproxy", NETWORK_SERVICE, PROXY_HOST, PROXY_PORT],
                           check=True, capture_output=True)
            subprocess.run(["networksetup", "-setwebproxy", NETWORK_SERVICE, PROXY_HOST, PROXY_PORT],
                           check=True, capture_output=True)
            logger.info(f"macOS proxy enabled: {PROXY_HOST}:{PROXY_PORT}")
        else:
            subprocess.run(["networksetup", "-setsecurewebproxystate", NETWORK_SERVICE, "off"],
                           check=True, capture_output=True)
            subprocess.run(["networksetup", "-setwebproxystate", NETWORK_SERVICE, "off"],
                           check=True, capture_output=True)
            logger.info("macOS proxy disabled")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"Failed to set macOS proxy: {e}")


# =============================================================================
# CLEANUP SAFETY NET
# =============================================================================

_cleanup_done = False


def _emergency_cleanup() -> None:
    """Emergency cleanup - disable proxy even if mitmproxy crashes."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    logger.info("Emergency cleanup: disabling system proxy...")
    _set_system_proxy(enable=False)


def _signal_handler(signum: int, frame) -> None:
    """Handle termination signals gracefully."""
    _ = frame  # Unused
    sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
    logger.info(f"Received signal {sig_name}, cleaning up...")
    _emergency_cleanup()
    # Re-raise the signal to let mitmproxy handle shutdown
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def _register_cleanup_handlers() -> None:
    """Register signal handlers and atexit for cleanup safety."""
    # atexit runs on normal exit or unhandled exception
    atexit.register(_emergency_cleanup)

    # Signal handlers for Ctrl+C (SIGINT) and termination (SIGTERM)
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    else:
        # Windows only supports SIGINT
        signal.signal(signal.SIGINT, _signal_handler)


# =============================================================================
# CERTIFICATE MANAGEMENT
# =============================================================================

CERT_DIR = Path("~/.mitmproxy").expanduser()
CERT_NAME = "oximy"  # Must match CONF_BASENAME in mitmproxy/options.py


def _get_cert_path() -> Path:
    """Get path to mitmproxy CA certificate."""
    return CERT_DIR / f"{CERT_NAME}-ca-cert.pem"


def _cert_exists() -> bool:
    """Check if mitmproxy CA certificate file exists."""
    return _get_cert_path().exists()


def _is_cert_trusted() -> bool:
    """Check if mitmproxy CA is trusted in macOS Keychain."""
    if sys.platform != "darwin":
        return True
    try:
        result = subprocess.run(
            ["security", "verify-cert", "-c", str(_get_cert_path())],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _install_cert() -> bool:
    """Install mitmproxy CA to macOS Keychain. Returns True on success."""
    if sys.platform != "darwin":
        return True
    cert_path = _get_cert_path()
    if not cert_path.exists():
        logger.error(f"Certificate not found: {cert_path}")
        return False

    try:
        # Try System keychain first (requires admin password prompt)
        # -p ssl is CRITICAL - without it, cert is added but not trusted for SSL
        result = subprocess.run(
            [
                "security", "add-trusted-cert",
                "-d",  # Admin cert store
                "-r", "trustRoot",  # Trust as root CA
                "-p", "ssl",  # Trust for SSL (REQUIRED!)
                "-k", "/Library/Keychains/System.keychain",
                str(cert_path)
            ],
            capture_output=True,
            timeout=60  # User needs time to enter password
        )

        if result.returncode == 0:
            logger.info("Certificate installed to System Keychain")
            return True

        # Fallback: try user's login keychain
        login_keychain = Path.home() / "Library/Keychains/login.keychain-db"
        result = subprocess.run(
            [
                "security", "add-trusted-cert",
                "-r", "trustRoot",
                "-p", "ssl",  # Trust for SSL (REQUIRED!)
                "-k", str(login_keychain),
                str(cert_path)
            ],
            capture_output=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("Certificate installed to login Keychain")
            return True

        logger.error(f"Failed to install certificate: {result.stderr.decode()}")
        return False

    except subprocess.TimeoutExpired:
        logger.error("Certificate installation timed out")
        return False
    except Exception as e:
        logger.error(f"Certificate installation failed: {e}")
        return False


def _ensure_cert_trusted() -> bool:
    """Ensure mitmproxy CA cert exists and is trusted. Returns True if ready."""
    if not _cert_exists():
        logger.warning("mitmproxy CA certificate not found. It will be generated on first request.")
        return False

    if _is_cert_trusted():
        logger.debug("Certificate already trusted")
        return True

    logger.info("Certificate not trusted - attempting installation...")
    return _install_cert()


# =============================================================================
# CONFIG LOADING
# =============================================================================

SENSOR_CONFIG_URL = "https://api.oximy.com/api/v1/sensor-config"
SENSOR_CONFIG_CACHE = Path("~/.oximy/sensor-config.json").expanduser()
CONFIG_REFRESH_INTERVAL_SECONDS = 1800  # 30 minutes


def fetch_sensor_config() -> dict:
    """Fetch sensor config from API and cache locally."""
    import urllib.request
    import urllib.error

    default_config = {
        "whitelist": [],
        "blacklist": [],
        "passthrough": [],
    }

    try:
        logger.info(f"Fetching sensor config from {SENSOR_CONFIG_URL}")
        req = urllib.request.Request(
            SENSOR_CONFIG_URL,
            headers={"User-Agent": "Oximy-Sensor/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        # Cache the raw response locally
        SENSOR_CONFIG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(SENSOR_CONFIG_CACHE, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        logger.info(f"Sensor config cached to {SENSOR_CONFIG_CACHE}")

        return _parse_sensor_config(raw)

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to fetch sensor config: {e}")

        if SENSOR_CONFIG_CACHE.exists():
            try:
                with open(SENSOR_CONFIG_CACHE, encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info(f"Using cached sensor config from {SENSOR_CONFIG_CACHE}")
                return _parse_sensor_config(cached)
            except (json.JSONDecodeError, IOError) as cache_err:
                logger.warning(f"Failed to load cached config: {cache_err}")

        logger.warning("Using empty default config")
        return default_config


def _parse_sensor_config(raw: dict) -> dict:
    """Parse API response into normalized config format."""
    data = raw.get("data", raw)
    return {
        "whitelist": data.get("whitelistedDomains", []),
        "blacklist": data.get("blacklistedWords", []),
        "passthrough": data.get("passthroughDomains", []),
    }


def load_output_config(config_path: Path | None = None) -> dict:
    """Load output configuration."""
    default = {"output": {"directory": "~/.oximy/traces", "filename_pattern": "traces_{date}.jsonl"}}
    if config_path and config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                user_config = json.load(f)
            if "output" in user_config:
                default["output"].update(user_config["output"])
        except (json.JSONDecodeError, IOError):
            pass
    return default


# =============================================================================
# DEVICE & WORKSPACE IDs
# =============================================================================

_device_id_cache: str | None = None


def get_device_id() -> str | None:
    """Get hardware UUID for this device. Cached after first call."""
    global _device_id_cache
    if _device_id_cache is not None:
        return _device_id_cache

    try:
        if sys.platform == "darwin":
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        parts = line.split('"')
                        if len(parts) >= 4:
                            _device_id_cache = parts[3]
                            return _device_id_cache
        elif sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "csproduct", "get", "UUID"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    uuid = lines[1].strip()
                    if uuid and uuid != "UUID":
                        _device_id_cache = uuid
                        return _device_id_cache
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug(f"Failed to get device ID: {e}")

    return None


# =============================================================================
# MATCHING
# =============================================================================

def matches_domain(host: str, patterns: list[str]) -> str | None:
    """Check if host matches any pattern. Returns matched pattern or None."""
    host_lower = host.lower()

    for pattern in patterns:
        pattern_lower = pattern.lower()

        # Exact match
        if host_lower == pattern_lower:
            return pattern

        # Wildcard prefix (*.example.com)
        if pattern_lower.startswith("*."):
            suffix = pattern_lower[1:]
            if host_lower.endswith(suffix) or host_lower == pattern_lower[2:]:
                return pattern

        # fnmatch for glob patterns
        if fnmatch.fnmatch(host_lower, pattern_lower):
            return pattern

        # Regex for patterns like bedrock-runtime.*.amazonaws.com
        if "*" in pattern and not pattern.startswith("*"):
            regex = pattern_lower.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{regex}$", host_lower):
                return pattern

    return None


def contains_blacklist_word(text: str, words: list[str]) -> str | None:
    """Check if text contains any blacklisted word. Returns the word or None."""
    if not text:
        return None
    text_lower = text.lower()
    for word in words:
        if word.lower() in text_lower:
            return word
    return None


# =============================================================================
# TLS PASSTHROUGH
# =============================================================================

LEARNED_PASSTHROUGH_CACHE = Path("~/.oximy/learned-passthrough.json").expanduser()


class TLSPassthrough:
    """Manages TLS passthrough for certificate-pinned hosts."""

    def __init__(self, patterns: list[str]):
        """Initialize with patterns from API config."""
        self._patterns: list[re.Pattern] = []
        self._learned_patterns: list[str] = []

        # Load patterns from API config
        for p in patterns:
            try:
                self._patterns.append(re.compile(p, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid passthrough pattern '{p}': {e}")

        # Load learned patterns from local cache
        self._load_learned()

    def _load_learned(self) -> None:
        """Load learned passthrough patterns from local cache."""
        if LEARNED_PASSTHROUGH_CACHE.exists():
            try:
                with open(LEARNED_PASSTHROUGH_CACHE, encoding="utf-8") as f:
                    data = json.load(f)
                self._learned_patterns = data.get("patterns", [])
                for p in self._learned_patterns:
                    try:
                        self._patterns.append(re.compile(p, re.IGNORECASE))
                    except re.error:
                        pass
                if self._learned_patterns:
                    logger.info(f"Loaded {len(self._learned_patterns)} learned passthrough patterns")
            except (json.JSONDecodeError, IOError):
                pass

    def should_passthrough(self, host: str) -> bool:
        """Check if host should bypass TLS interception."""
        return any(p.match(host) for p in self._patterns)

    def add_host(self, host: str) -> None:
        """Add a learned host to local passthrough cache."""
        try:
            pattern = f"^{re.escape(host)}$"
            if pattern in self._learned_patterns:
                return

            self._learned_patterns.append(pattern)
            self._patterns.append(re.compile(pattern, re.IGNORECASE))

            # Save to local cache
            LEARNED_PASSTHROUGH_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(LEARNED_PASSTHROUGH_CACHE, "w", encoding="utf-8") as f:
                json.dump({"patterns": self._learned_patterns}, f, indent=2)
            logger.info(f"Added to learned passthrough: {host}")
        except (IOError, re.error) as e:
            logger.warning(f"Failed to save learned passthrough: {e}")

    def record_tls_failure(self, host: str, error: str, whitelist: list[str]) -> None:
        """Record TLS failure - add to passthrough if certificate pinning detected."""
        # Never passthrough whitelisted domains
        if matches_domain(host, whitelist):
            return

        pinning_indicators = [
            "certificate verify failed", "unknown ca", "bad certificate",
            "certificate_unknown", "self signed certificate",
            "client disconnected during the handshake",
        ]

        if any(ind in error.lower() for ind in pinning_indicators):
            self.add_host(host)

    def update_passthrough(self, patterns: list[str]) -> None:
        """Update passthrough patterns from refreshed config."""
        new_patterns: list[re.Pattern] = []
        for p in patterns:
            try:
                new_patterns.append(re.compile(p, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid passthrough pattern '{p}': {e}")
        # Re-add learned patterns
        for p in self._learned_patterns:
            try:
                new_patterns.append(re.compile(p, re.IGNORECASE))
            except re.error:
                pass
        self._patterns = new_patterns
        logger.debug(f"Updated passthrough patterns: {len(patterns)} from config + {len(self._learned_patterns)} learned")


# =============================================================================
# TRACE WRITER
# =============================================================================

class TraceWriter:
    """Writes trace events to rotating JSONL files."""

    def __init__(self, output_dir: Path, filename_pattern: str = "traces_{date}.jsonl"):
        self.output_dir = Path(output_dir).expanduser()
        self.filename_pattern = filename_pattern
        self._current_file: Path | None = None
        self._fo: IO[str] | None = None
        self._count = 0

    def write(self, event: dict) -> None:
        """Write an event to the current JSONL file."""
        self._maybe_rotate()
        if self._fo is None:
            return
        try:
            self._fo.write(json.dumps(event, separators=(",", ":")) + "\n")
            self._fo.flush()
            self._count += 1
        except (IOError, OSError) as e:
            logger.error(f"Write failed: {e}")

    def _maybe_rotate(self) -> None:
        """Rotate to new file if date changed."""
        expected = self.output_dir / self.filename_pattern.format(date=date.today().isoformat())
        if self._current_file == expected:
            return

        if self._fo:
            self._fo.close()
            self._fo = None

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._fo = open(expected, "a", encoding="utf-8", buffering=1)
            self._current_file = expected
            logger.info(f"Trace file: {expected}")
        except IOError as e:
            logger.error(f"Failed to open trace file: {e}")

    def close(self) -> None:
        """Close file handle."""
        if self._fo:
            self._fo.close()
            logger.info(f"Closed trace file ({self._count} events)")
            self._fo = None


# =============================================================================
# TRACE UPLOADER
# =============================================================================

INGEST_API_URL = "https://api.oximy.com/api/v1/ingest/network-traces"
UPLOAD_STATE_FILE = Path("~/.oximy/upload-state.json").expanduser()
FORCE_SYNC_TRIGGER = Path("~/.oximy/force-sync").expanduser()  # Trigger file for immediate sync
BATCH_SIZE = 500  # Traces per upload batch
UPLOAD_INTERVAL_SECONDS = 2  # Upload every N seconds
UPLOAD_THRESHOLD_COUNT = 100  # Or every N traces


class TraceUploader:
    """Uploads traces to the ingestion API with gzip compression."""

    def __init__(self):
        self._upload_state: dict[str, int] = {}  # file_path -> last_uploaded_line
        self._load_state()

    def _load_state(self) -> None:
        """Load upload state from disk."""
        if UPLOAD_STATE_FILE.exists():
            try:
                with open(UPLOAD_STATE_FILE, encoding="utf-8") as f:
                    self._upload_state = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_state(self) -> None:
        """Save upload state to disk."""
        try:
            UPLOAD_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(UPLOAD_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._upload_state, f)
        except IOError as e:
            logger.warning(f"Failed to save upload state: {e}")

    def upload_traces(self, trace_file: Path) -> int:
        """Upload pending traces from a file. Returns number of traces uploaded."""
        import gzip
        import urllib.request
        import urllib.error

        if not trace_file.exists():
            return 0

        file_key = str(trace_file)
        last_uploaded = self._upload_state.get(file_key, 0)

        # Read all lines from the file
        try:
            with open(trace_file, encoding="utf-8") as f:
                lines = f.readlines()
        except IOError as e:
            logger.warning(f"Failed to read trace file: {e}")
            return 0

        # Get pending lines (not yet uploaded)
        pending_lines = lines[last_uploaded:]
        if not pending_lines:
            return 0

        total_uploaded = 0

        # Upload in batches
        for i in range(0, len(pending_lines), BATCH_SIZE):
            batch = pending_lines[i:i + BATCH_SIZE]
            batch_data = "".join(batch).encode("utf-8")

            # Gzip compress the batch
            compressed = gzip.compress(batch_data)

            try:
                req = urllib.request.Request(
                    INGEST_API_URL,
                    data=compressed,
                    headers={
                        "Content-Type": "application/jsonl",
                        "Content-Encoding": "gzip",
                        "User-Agent": "Oximy-Sensor/1.0",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    response_data = json.loads(resp.read().decode("utf-8"))

                if response_data.get("success"):
                    uploaded_count = len(batch)
                    total_uploaded += uploaded_count
                    last_uploaded += uploaded_count
                    self._upload_state[file_key] = last_uploaded
                    self._save_state()
                    logger.info(f"Uploaded {uploaded_count} traces (batch {i // BATCH_SIZE + 1})")
                else:
                    logger.warning(f"Upload failed: {response_data.get('error', 'Unknown error')}")
                    break

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                logger.warning(f"Upload HTTP error {e.code}: {error_body[:200]}")
                break
            except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
                logger.warning(f"Upload failed: {e}")
                break

        return total_uploaded

    def upload_all_pending(self, traces_dir: Path) -> int:
        """Upload all pending traces from all files in the directory."""
        if not traces_dir.exists():
            return 0

        total = 0
        for trace_file in sorted(traces_dir.glob("traces_*.jsonl")):
            uploaded = self.upload_traces(trace_file)
            total += uploaded

        return total


def generate_event_id() -> str:
    """Generate UUID v7 (time-sortable)."""
    ts = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    uuid_int = (ts << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    h = f"{uuid_int:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# =============================================================================
# MAIN ADDON
# =============================================================================

class OximyAddon:
    """Captures AI API traffic with whitelist/blacklist filtering."""

    def __init__(self):
        self._enabled = False
        self._whitelist: list[str] = []
        self._blacklist: list[str] = []
        self._tls: TLSPassthrough | None = None
        self._writer: TraceWriter | None = None
        self._uploader: TraceUploader | None = None
        self._resolver: ProcessResolver | None = None
        self._device_id: str | None = None
        self._output_dir: Path | None = None
        self._last_upload_time: float = 0
        self._traces_since_upload: int = 0
        self._config_refresh_thread: threading.Thread | None = None
        self._config_refresh_stop: threading.Event = threading.Event()
        self._config_lock: threading.Lock = threading.Lock()  # Protects config updates
        self._force_sync_thread: threading.Thread | None = None
        self._force_sync_stop: threading.Event = threading.Event()

    def _get_config_snapshot(self) -> tuple[list[str], list[str]]:
        """Get a consistent snapshot of whitelist and blacklist.

        Returns copies to ensure the caller has immutable references
        that won't change during processing.
        """
        with self._config_lock:
            return list(self._whitelist), list(self._blacklist)

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option("oximy_enabled", bool, False, "Enable AI traffic capture")
        loader.add_option("oximy_config", str, "", "Path to config.json")
        loader.add_option("oximy_output_dir", str, "~/.oximy/traces", "Output directory")
        loader.add_option("oximy_verbose", bool, False, "Verbose logging")
        loader.add_option("oximy_upload_enabled", bool, True, "Enable trace uploads (disable if host app handles sync)")

    def _refresh_config(self, max_retries: int = 3) -> bool:
        """Fetch and apply updated config from API with retries.

        Returns True if config was successfully refreshed, False otherwise.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                raw_config = fetch_sensor_config()
                config = _parse_sensor_config(raw_config)

                # Atomic update with lock to ensure consistent state
                with self._config_lock:
                    self._whitelist = config.get("whitelist", [])
                    self._blacklist = config.get("blacklist", [])

                    # Update TLS passthrough patterns
                    if self._tls:
                        self._tls.update_passthrough(config.get("passthrough", []))

                logger.info(f"Config refreshed: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist")
                return True

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 20s
                    backoff = 5 * (2 ** attempt)
                    logger.warning(f"Config refresh attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {backoff}s...")
                    # Use interruptible sleep
                    if self._config_refresh_stop.wait(timeout=backoff):
                        return False  # Stop requested during backoff

        logger.warning(f"Config refresh failed after {max_retries} attempts: {last_error}")
        return False

    def _start_config_refresh_task(self) -> None:
        """Start background thread to periodically refresh config."""
        self._config_refresh_stop.clear()

        def refresh_loop():
            while not self._config_refresh_stop.is_set():
                # Wait with interruptible sleep
                if self._config_refresh_stop.wait(timeout=CONFIG_REFRESH_INTERVAL_SECONDS):
                    break  # Stop event was set
                if not self._enabled:
                    break
                self._refresh_config()

        self._config_refresh_thread = threading.Thread(
            target=refresh_loop,
            daemon=True,
            name="oximy-config-refresh"
        )
        self._config_refresh_thread.start()
        logger.info(f"Config refresh task started (interval: {CONFIG_REFRESH_INTERVAL_SECONDS}s)")

    def _start_force_sync_monitor(self) -> None:
        """Start background thread to monitor for force-sync trigger file."""
        self._force_sync_stop.clear()

        def monitor_loop():
            while not self._force_sync_stop.is_set():
                # Check every 0.5 seconds for force-sync trigger
                if self._force_sync_stop.wait(timeout=0.5):
                    break
                if not self._enabled:
                    break

                # Check for trigger file
                if FORCE_SYNC_TRIGGER.exists():
                    logger.info("Force sync trigger detected")
                    try:
                        FORCE_SYNC_TRIGGER.unlink()  # Delete trigger file
                    except OSError:
                        pass

                    # Perform immediate upload
                    if self._uploader and self._output_dir:
                        try:
                            if self._writer and self._writer._fo:
                                self._writer._fo.flush()
                            uploaded = self._uploader.upload_all_pending(self._output_dir)
                            if uploaded > 0:
                                logger.info(f"Force sync: uploaded {uploaded} traces")
                            else:
                                logger.info("Force sync: no pending traces to upload")
                        except Exception as e:
                            logger.warning(f"Force sync failed: {e}")

        self._force_sync_thread = threading.Thread(
            target=monitor_loop,
            daemon=True,
            name="oximy-force-sync-monitor"
        )
        self._force_sync_thread.start()
        logger.debug("Force sync monitor started")

    def configure(self, updated: set[str]) -> None:
        """Handle configuration changes."""
        _ = updated  # Unused but required by mitmproxy API
        if not ctx.options.oximy_enabled:
            if self._enabled:
                self._cleanup()
            self._enabled = False
            return

        self._enabled = True
        logger.setLevel(logging.DEBUG if ctx.options.oximy_verbose else logging.INFO)

        # Register cleanup handlers for graceful shutdown
        _register_cleanup_handlers()

        # Check certificate before anything else (macOS only)
        if sys.platform == "darwin":
            if not _ensure_cert_trusted():
                logger.error("=" * 60)
                logger.error("CERTIFICATE NOT TRUSTED - HTTPS interception will fail!")
                logger.error("To install manually, run:")
                logger.error(f"  sudo security add-trusted-cert -d -r trustRoot -p ssl -k /Library/Keychains/System.keychain {_get_cert_path()}")
                logger.error("=" * 60)
                # Continue anyway - user might install manually or cert will be generated

        # Fetch sensor config from API (cached locally)
        sensor_config = fetch_sensor_config()
        self._whitelist = sensor_config.get("whitelist", [])
        self._blacklist = sensor_config.get("blacklist", [])
        passthrough_patterns = sensor_config.get("passthrough", [])
        self._tls = TLSPassthrough(passthrough_patterns)

        # Start periodic config refresh (only if not already running)
        if self._config_refresh_thread is None or not self._config_refresh_thread.is_alive():
            self._start_config_refresh_task()

        # Start background trigger file monitor
        self._start_force_sync_monitor()

        output_config = load_output_config(Path(ctx.options.oximy_config) if ctx.options.oximy_config else None)
        self._output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = TraceWriter(self._output_dir, output_config["output"].get("filename_pattern", "traces_{date}.jsonl"))

        # Initialize trace uploader for API uploads (only if enabled)
        # When running under a host app (e.g., OximyMac), the host handles sync
        if ctx.options.oximy_upload_enabled:
            self._uploader = TraceUploader()
            self._last_upload_time = time.time()
            self._traces_since_upload = 0
            logger.info("Trace upload enabled (addon handles sync)")
        else:
            self._uploader = None
            logger.info("Trace upload disabled (host app handles sync)")

        # Initialize process resolver for client attribution
        self._resolver = ProcessResolver()

        # Get device ID
        self._device_id = get_device_id()
        logger.info(f"Device ID: {self._device_id}")

        _set_system_proxy(enable=True)
        logger.info(f"===== OXIMY READY: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist, {len(passthrough_patterns)} passthrough =====")

    def _check_blacklist(self, *texts: str, blacklist: list[str] | None = None) -> str | None:
        """Check if any text contains a blacklisted word.

        Args:
            texts: Strings to check for blacklisted words
            blacklist: Optional list to use (defaults to self._blacklist)
        """
        bl = blacklist if blacklist is not None else self._blacklist
        for text in texts:
            if word := contains_blacklist_word(text, bl):
                return word
        return None

    # =========================================================================
    # TLS Hooks
    # =========================================================================

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """Passthrough check - skip TLS interception for pinned hosts."""
        if not self._enabled or not self._tls:
            return

        host = data.client_hello.sni or (data.context.server.address[0] if data.context.server.address else None)
        if host and self._tls.should_passthrough(host):
            data.ignore_connection = True
            logger.debug(f"PASSTHROUGH: {host}")

    def tls_failed_client(self, data: tls.TlsData) -> None:
        """Learn certificate-pinned hosts from TLS failures."""
        if not self._enabled or not self._tls:
            return

        host = data.context.server.sni or (data.context.server.address[0] if data.context.server.address else None)
        if host:
            error = str(data.conn.error) if data.conn.error else ""
            self._tls.record_tls_failure(host, error, self._whitelist)

    # =========================================================================
    # HTTP Hooks
    # =========================================================================

    async def request(self, flow: http.HTTPFlow) -> None:
        """Check whitelist and blacklist on request."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        logger.info(f">>> {flow.request.method} {url[:100]}")

        # Whitelist check
        if not matches_domain(host, self._whitelist):
            flow.metadata["oximy_skip"] = True
            return

        # Blacklist check on URL only
        if word := self._check_blacklist(url):
            logger.info(f"[BLACKLISTED] {url[:80]} (matched: {word})")
            flow.metadata["oximy_skip"] = True
            return

        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_start"] = time.time()

        # Get client process info
        if self._resolver and flow.client_conn and flow.client_conn.peername:
            try:
                client_port = flow.client_conn.peername[1]
                client_process = await self._resolver.get_process_for_port(client_port)
                flow.metadata["oximy_client"] = client_process
                logger.debug(f"Client: {client_process.name} (PID {client_process.pid})")
            except Exception as e:
                logger.debug(f"Failed to get client process: {e}")

    def response(self, flow: http.HTTPFlow) -> None:
        """Write trace for captured response."""
        if not self._enabled or not self._writer:
            return

        if flow.metadata.get("oximy_skip") or flow.websocket:
            return

        if not flow.response:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        response_body = ""
        if flow.response.content:
            try:
                response_body = flow.response.content.decode("utf-8", errors="replace")
            except Exception:
                pass

        event = self._build_event(flow, response_body)
        self._writer.write(event)
        self._traces_since_upload += 1
        logger.info(f"<<< CAPTURED: {flow.request.method} {url[:80]} [{flow.response.status_code}]")

        # Check if we should upload
        self._maybe_upload()

    def _build_event(self, flow: http.HTTPFlow, response_body: str) -> dict:
        """Build trace event."""
        request_body = None
        if flow.request.content:
            try:
                request_body = flow.request.content.decode("utf-8")
            except UnicodeDecodeError:
                request_body = flow.request.content.hex()

        duration_ms = ttfb_ms = None
        if flow.request.timestamp_start and flow.response:
            if flow.response.timestamp_end:
                duration_ms = int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000)
            if flow.response.timestamp_start:
                ttfb_ms = int((flow.response.timestamp_start - flow.request.timestamp_start) * 1000)

        # Filter out cookie headers for privacy
        request_headers = {k: v for k, v in flow.request.headers.items() if k.lower() != "cookie"}
        response_headers = {k: v for k, v in flow.response.headers.items() if k.lower() != "set-cookie"} if flow.response else {}

        # Build client info from stored process data
        client_info: dict | None = None
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")
        if client_process:
            client_info = {
                "pid": client_process.pid,
                "bundle_id": client_process.bundle_id,
            }
            if client_process.name:
                client_info["name"] = client_process.name

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "http",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info
        if client_info:
            event["client"] = client_info

        # Add request/response/timing
        event["request"] = {
            "method": flow.request.method,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "headers": request_headers,
            "body": request_body,
        }
        event["response"] = {
            "status_code": flow.response.status_code if flow.response else None,
            "headers": response_headers,
            "body": response_body if response_body else None,
        }
        event["timing"] = {"duration_ms": duration_ms, "ttfb_ms": ttfb_ms}

        return event

    # =========================================================================
    # WebSocket Hooks
    # =========================================================================

    async def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Accumulate WebSocket messages."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        if not matches_domain(host, self._whitelist):
            flow.metadata["oximy_skip"] = True
            return

        if "oximy_ws_messages" not in flow.metadata:
            # Blacklist check on URL only (first message)
            if word := self._check_blacklist(url):
                logger.info(f"[BLACKLISTED] WS {url[:80]} (matched: {word})")
                flow.metadata["oximy_skip"] = True
                return

            flow.metadata["oximy_ws_messages"] = []
            flow.metadata["oximy_ws_start"] = time.time()

            if self._resolver and flow.client_conn and flow.client_conn.peername:
                try:
                    client_port = flow.client_conn.peername[1]
                    client_process = await self._resolver.get_process_for_port(client_port)
                    flow.metadata["oximy_client"] = client_process
                except Exception as e:
                    logger.debug(f"Failed to get client process for WS: {e}")

        if flow.websocket and flow.websocket.messages:
            msg = flow.websocket.messages[-1]
            content = msg.content.decode("utf-8", errors="replace") if isinstance(msg.content, bytes) else str(msg.content)
            flow.metadata["oximy_ws_messages"].append({
                "direction": "client" if msg.from_client else "server",
                "timestamp": datetime.fromtimestamp(msg.timestamp, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "content": content,
            })

    def websocket_end(self, flow: http.HTTPFlow) -> None:
        """Write WebSocket trace on connection close."""
        if not self._enabled or not self._writer:
            return

        if flow.metadata.get("oximy_skip"):
            return

        messages = flow.metadata.get("oximy_ws_messages")
        if not messages:
            return

        start = flow.metadata.get("oximy_ws_start", time.time())

        # Build client info from stored process data
        client_info: dict | None = None
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")
        if client_process:
            client_info = {
                "pid": client_process.pid,
                "bundle_id": client_process.bundle_id,
            }
            if client_process.name:
                client_info["name"] = client_process.name

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info
        if client_info:
            event["client"] = client_info

        # Add WebSocket-specific fields
        event["host"] = flow.request.pretty_host
        event["path"] = flow.request.path
        event["messages"] = messages
        event["timing"] = {"duration_ms": int((time.time() - start) * 1000), "message_count": len(messages)}

        self._writer.write(event)
        self._traces_since_upload += 1
        logger.info(f"<<< CAPTURED WS: {flow.request.pretty_host} ({len(messages)} messages)")

        # Check if we should upload
        self._maybe_upload()

    # =========================================================================
    # Upload Trigger
    # =========================================================================

    def _maybe_upload(self) -> None:
        """Upload traces if threshold reached (100 traces or 2 seconds elapsed) or force-sync triggered."""
        if not self._uploader or not self._output_dir:
            return

        now = time.time()
        time_elapsed = now - self._last_upload_time >= UPLOAD_INTERVAL_SECONDS
        count_reached = self._traces_since_upload >= UPLOAD_THRESHOLD_COUNT

        # Check for force-sync trigger from host app
        force_sync = FORCE_SYNC_TRIGGER.exists()
        if force_sync:
            logger.info("Force sync triggered by host app")
            try:
                FORCE_SYNC_TRIGGER.unlink()  # Delete trigger file
            except OSError:
                pass

        # Upload if either condition is met and we have traces (or force sync)
        if (time_elapsed or count_reached or force_sync) and self._traces_since_upload > 0:
            try:
                # Flush writer before uploading
                if self._writer and self._writer._fo:
                    self._writer._fo.flush()

                uploaded = self._uploader.upload_all_pending(self._output_dir)
                if uploaded > 0:
                    logger.info(f"Uploaded {uploaded} traces to API")

                self._last_upload_time = now
                self._traces_since_upload = 0
            except Exception as e:
                logger.warning(f"Failed to upload traces: {e}")
        elif force_sync:
            # Force sync but no pending traces - still try to upload any existing files
            try:
                if self._writer and self._writer._fo:
                    self._writer._fo.flush()
                uploaded = self._uploader.upload_all_pending(self._output_dir)
                if uploaded > 0:
                    logger.info(f"Force sync: uploaded {uploaded} traces to API")
            except Exception as e:
                logger.warning(f"Force sync failed: {e}")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def done(self) -> None:
        """Cleanup on shutdown."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        global _cleanup_done
        if _cleanup_done:
            return
        _cleanup_done = True

        # Stop config refresh thread
        self._config_refresh_stop.set()
        if self._config_refresh_thread and self._config_refresh_thread.is_alive():
            self._config_refresh_thread.join(timeout=2)

        # Stop force sync monitor thread
        self._force_sync_stop.set()
        if self._force_sync_thread and self._force_sync_thread.is_alive():
            self._force_sync_thread.join(timeout=1)

        _set_system_proxy(enable=False)

        # Close writer first to flush pending writes
        if self._writer:
            self._writer.close()
            self._writer = None

        # Upload pending traces to API
        if self._uploader and self._output_dir:
            try:
                uploaded = self._uploader.upload_all_pending(self._output_dir)
                if uploaded > 0:
                    logger.info(f"Uploaded {uploaded} traces to API on shutdown")
            except Exception as e:
                logger.warning(f"Failed to upload traces on shutdown: {e}")

        self._enabled = False
        logger.info("Oximy addon disabled")


addons = [OximyAddon()]
