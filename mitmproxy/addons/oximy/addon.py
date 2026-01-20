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
from urllib.parse import urlparse

from mitmproxy import ctx, http, tls
print("*" * 100)
print("Oximy addon loaded")
print("*" * 100)
# Import ProcessResolver - handle both package and script modes
try:
    from .process import ClientProcess, ProcessResolver
except ImportError:
    from process import ClientProcess, ProcessResolver

# Import normalize - handle both package and script modes
try:
    from .normalize import normalize_body
except ImportError:
    from normalize import normalize_body

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

DEFAULT_SENSOR_CONFIG_URL = "https://api.oximy.com/api/v1/sensor-config"
DEFAULT_SENSOR_CONFIG_CACHE = "~/.oximy/sensor-config.json"
DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS = 1800  # 30 minutes (fallback)


def fetch_sensor_config(
    url: str = DEFAULT_SENSOR_CONFIG_URL,
    cache_path: str = DEFAULT_SENSOR_CONFIG_CACHE,
) -> dict:
    """Fetch sensor config from API and cache locally."""
    import urllib.request
    import urllib.error

    cache_file = Path(cache_path).expanduser()

    default_config = {
        "whitelist": [],
        "blacklist": [],
        "passthrough": [],
    }

    try:
        logger.info(f"Fetching sensor config from {url}")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Oximy-Sensor/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        # Cache the raw response locally
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        logger.info(f"Sensor config cached to {cache_file}")

        return _parse_sensor_config(raw)

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to fetch sensor config: {e}")

        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info(f"Using cached sensor config from {cache_file}")
                return _parse_sensor_config(cached)
            except (json.JSONDecodeError, IOError) as cache_err:
                logger.warning(f"Failed to load cached config: {cache_err}")

        logger.warning("Using empty default config")
        return default_config


def _parse_sensor_config(raw: dict) -> dict:
    """Parse API response into normalized config format."""
    data = raw.get("data", raw)

    # Parse allowed_app_origins (hosts = browsers, non_hosts = AI-native apps)
    app_origins = data.get("allowed_app_origins", {})

    return {
        "whitelist": data.get("whitelistedDomains", []),
        "blacklist": data.get("blacklistedWords", []),
        "passthrough": data.get("passthroughDomains", []),
        "allowed_app_origins": {
            "hosts": app_origins.get("hosts", []),
            "non_hosts": app_origins.get("non_hosts", []),
        },
        "allowed_host_origins": data.get("allowed_host_origins", []),
    }


DEFAULT_CONFIG_PATH = Path("~/.oximy/config.json").expanduser()


def load_output_config(config_path: Path | None = None) -> dict:
    """Load output configuration.

    Checks the following paths in order:
    1. Explicitly provided config_path
    2. Default path: ~/.oximy/config.json
    """
    default = {
        "output": {"directory": "~/.oximy/traces", "filename_pattern": "traces_{date}.jsonl"},
        "sensor_config_url": DEFAULT_SENSOR_CONFIG_URL,
        "sensor_config_cache": DEFAULT_SENSOR_CONFIG_CACHE,
        "config_refresh_interval_seconds": DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS,
    }

    # Determine which config file to load
    paths_to_check = []
    if config_path:
        paths_to_check.append(config_path)
    paths_to_check.append(DEFAULT_CONFIG_PATH)

    for path in paths_to_check:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    user_config = json.load(f)
                if "output" in user_config:
                    default["output"].update(user_config["output"])
                if "sensor_config_url" in user_config:
                    default["sensor_config_url"] = user_config["sensor_config_url"]
                if "sensor_config_cache" in user_config:
                    default["sensor_config_cache"] = user_config["sensor_config_cache"]
                if "config_refresh_interval_seconds" in user_config:
                    default["config_refresh_interval_seconds"] = user_config["config_refresh_interval_seconds"]
                logger.debug(f"Loaded config from {path}")
                break
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Failed to load config from {path}: {e}")

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


def _matches_url_pattern(url: str, pattern: str) -> bool:
    """Match full URL against pattern with glob support.

    Supports:
    - ** matches any characters including /
    - * matches any characters except /
    - *.domain.com/** matches subdomains with any path
    """
    url_lower = url.lower()
    pattern_lower = pattern.lower()

    # Handle *.domain.com patterns - special handling for subdomain wildcards with paths
    if pattern_lower.startswith("*."):
        # Extract domain part (e.g., "replit.com" from "*.replit.com/**")
        rest = pattern_lower[2:]  # Remove "*."
        slash_idx = rest.find('/')
        if slash_idx != -1:
            domain = rest[:slash_idx]
            path_pattern = rest[slash_idx:]
        else:
            domain = rest
            path_pattern = ""

        # Parse URL to get host and path
        url_slash_idx = url_lower.find('/')
        if url_slash_idx != -1:
            url_host = url_lower[:url_slash_idx]
            url_path = url_lower[url_slash_idx:]
        else:
            url_host = url_lower
            url_path = ""

        # Check if URL host ends with .domain or equals domain
        if not (url_host.endswith(f".{domain}") or url_host == domain):
            return False

        # If no path pattern or wildcard all paths, match any path
        if not path_pattern or path_pattern == "/**":
            return True

        # Match the remaining path pattern against URL path
        pattern_lower = path_pattern
        url_lower = url_path

    # Convert glob pattern to regex, handling special cases
    # /**/ should match zero or more path segments (e.g., "/" or "/foo/bar/")
    regex = ""
    i = 0
    while i < len(pattern_lower):
        # Handle /**/ - matches "/" or "/anything/"
        if pattern_lower[i:i+4] == "/**/":
            regex += "(?:/|/.*/)"
            i += 4
        # Handle ** at end or followed by non-slash - matches any characters including /
        elif i < len(pattern_lower) - 1 and pattern_lower[i:i+2] == "**":
            regex += ".*"
            i += 2
        # Handle * - matches any characters except /
        elif pattern_lower[i] == "*":
            regex += "[^/]*"
            i += 1
        # Escape regex metacharacters
        elif pattern_lower[i] in ".?+^${}[]|()":
            regex += "\\" + pattern_lower[i]
            i += 1
        else:
            regex += pattern_lower[i]
            i += 1

    return bool(re.match(f"^{regex}", url_lower))


def matches_whitelist(host: str, path: str, patterns: list[str]) -> str | None:
    """Check if host+path matches any whitelist pattern.

    Patterns can be:
    - Domain only: 'api.openai.com' or '*.openai.com' - matches any path
    - Domain + path: 'gemini.google.com/**/StreamGenerate*' - matches specific paths

    For patterns with paths:
    - ** matches any path segments (including /)
    - * matches any characters except /
    """
    full_url = f"{host}{path}"  # path already starts with /

    for pattern in patterns:
        # Check if pattern contains a path component
        # Look for / that's not part of *.domain pattern
        pattern_lower = pattern.lower()

        # Find first / that indicates a path
        first_slash = pattern.find('/')

        # Patterns starting with *. are domain wildcards, check if there's a path after domain
        if pattern.startswith("*."):
            # *.example.com or *.example.com/path
            rest_after_star = pattern[2:]
            slash_in_rest = rest_after_star.find('/')
            has_path = slash_in_rest != -1
        else:
            has_path = first_slash != -1

        if not has_path:
            # Domain-only pattern - use existing domain matching
            if matches_domain(host, [pattern]):
                return pattern
        else:
            # URL pattern with path - match full URL
            if _matches_url_pattern(full_url, pattern):
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


def extract_graphql_operation(body: bytes | None) -> str | None:
    """Extract GraphQL operation name from request body.

    Handles both single operations and batched operations.
    Returns the operation name or None if not a GraphQL request.
    """
    if not body:
        return None

    try:
        text = body.decode('utf-8')
        data = json.loads(text)

        # Handle batched operations (array of queries)
        if isinstance(data, list):
            # Return first operation name from batch
            for item in data:
                if isinstance(item, dict) and 'operationName' in item:
                    return item['operationName']
            return None

        # Single operation
        if isinstance(data, dict):
            return data.get('operationName')

    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

    return None


# =============================================================================
# HIERARCHICAL FILTERING: APP & HOST ORIGINS
# =============================================================================


def matches_app_origin(
    bundle_id: str | None,
    hosts: list[str],
    non_hosts: list[str],
) -> str | None:
    """Determine app type from bundle_id.

    Args:
        bundle_id: The app's bundle identifier (e.g., 'com.google.Chrome')
        hosts: List of browser bundle IDs (apps that can run AI websites)
        non_hosts: List of AI-native app bundle IDs

    Returns:
        "host" if bundle_id matches a browser
        "non_host" if bundle_id matches an AI-native app
        None if bundle_id doesn't match (request should be skipped)
    """
    if not bundle_id:
        return None

    bundle_lower = bundle_id.lower()

    # Check non_hosts first (AI-native apps - more specific)
    for pattern in non_hosts:
        if bundle_lower == pattern.lower():
            return "non_host"

    # Check hosts (browsers)
    for pattern in hosts:
        if bundle_lower == pattern.lower():
            return "host"

    return None


def matches_host_origin(origin: str | None, allowed_origins: list[str]) -> bool:
    """Check if request origin matches allowed host origins.

    Supports exact match and subdomain matching.

    Args:
        origin: The origin domain (e.g., 'chatgpt.com', 'chat.openai.com')
        allowed_origins: List of allowed origin domains

    Returns:
        True if origin matches an allowed origin, False otherwise
    """
    if not origin:
        return False

    origin_lower = origin.lower()

    for allowed in allowed_origins:
        allowed_lower = allowed.lower()

        # Exact match
        if origin_lower == allowed_lower:
            return True

        # Subdomain match (origin ends with .allowed)
        if origin_lower.endswith(f".{allowed_lower}"):
            return True

    return False


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

        # stop adding to learned hosts
        if any(ind in error.lower() for ind in pinning_indicators):
            self.add_host(host)
            # pass

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

        # Handle file truncation/recreation: if file has fewer lines than recorded,
        # reset state and upload from the beginning
        if len(lines) < last_uploaded:
            logger.info(f"Trace file was truncated/recreated (had {last_uploaded}, now {len(lines)}), resetting upload state")
            last_uploaded = 0
            self._upload_state[file_key] = 0
            self._save_state()

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
        # Hierarchical filtering: app origins and host origins
        self._allowed_app_hosts: list[str] = []  # Browser bundle IDs
        self._allowed_app_non_hosts: list[str] = []  # AI-native app bundle IDs
        self._allowed_host_origins: list[str] = []  # Website origins (for browsers)
        self._tls: TLSPassthrough | None = None
        self._writer: TraceWriter | None = None
        self._debug_writer: TraceWriter | None = None  # Unfiltered logs
        self._uploader: TraceUploader | None = None
        self._resolver: ProcessResolver | None = None
        self._device_id: str | None = None
        self._output_dir: Path | None = None
        self._last_upload_time: float = 0
        self._traces_since_upload: int = 0
        self._sensor_config_url: str = DEFAULT_SENSOR_CONFIG_URL
        self._sensor_config_cache: str = DEFAULT_SENSOR_CONFIG_CACHE
        self._config_refresh_interval: int = DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS
        self._config_refresh_thread: threading.Thread | None = None
        self._config_refresh_stop: threading.Event = threading.Event()
        self._config_lock: threading.Lock = threading.Lock()  # Protects config updates
        self._force_sync_thread: threading.Thread | None = None
        self._force_sync_stop: threading.Event = threading.Event()

    def _get_config_snapshot(self) -> dict:
        """Get a consistent snapshot of all filtering config.

        Returns copies to ensure the caller has immutable references
        that won't change during processing.
        """
        with self._config_lock:
            return {
                "whitelist": list(self._whitelist),
                "blacklist": list(self._blacklist),
                "allowed_app_hosts": list(self._allowed_app_hosts),
                "allowed_app_non_hosts": list(self._allowed_app_non_hosts),
                "allowed_host_origins": list(self._allowed_host_origins),
            }

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option("oximy_enabled", bool, False, "Enable AI traffic capture")
        loader.add_option("oximy_config", str, "", "Path to config.json")
        loader.add_option("oximy_output_dir", str, "~/.oximy/traces", "Output directory")
        loader.add_option("oximy_verbose", bool, False, "Verbose logging")
        loader.add_option("oximy_upload_enabled", bool, True, "Enable trace uploads (disable if host app handles sync)")
        loader.add_option("oximy_debug_traces", bool, False, "Log all requests to all_traces file (unfiltered)")
        

    def _refresh_config(self, max_retries: int = 3) -> bool:
        """Fetch and apply updated config from API with retries.

        Returns True if config was successfully refreshed, False otherwise.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                raw_config = fetch_sensor_config(self._sensor_config_url, self._sensor_config_cache)
                config = _parse_sensor_config(raw_config)

                # Atomic update with lock to ensure consistent state
                with self._config_lock:
                    self._whitelist = config.get("whitelist", [])
                    self._blacklist = config.get("blacklist", [])

                    # Update hierarchical filtering config
                    app_origins = config.get("allowed_app_origins", {})
                    self._allowed_app_hosts = app_origins.get("hosts", [])
                    self._allowed_app_non_hosts = app_origins.get("non_hosts", [])
                    self._allowed_host_origins = config.get("allowed_host_origins", [])

                    # Update TLS passthrough patterns
                    if self._tls:
                        self._tls.update_passthrough(config.get("passthrough", []))

                logger.info(
                    f"Config refreshed: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist, "
                    f"{len(self._allowed_app_hosts)} app_hosts, {len(self._allowed_host_origins)} host_origins"
                )
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
        interval = self._config_refresh_interval

        def refresh_loop():
            while not self._config_refresh_stop.is_set():
                # Wait with interruptible sleep
                if self._config_refresh_stop.wait(timeout=interval):
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
        logger.info(f"Config refresh task started (interval: {interval}s)")

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
            else:
                logger.info("***** OXIMY CERTIFICATE TRUSTED ****")

        # Load local config (output settings, refresh interval, etc.)
        output_config = load_output_config(Path(ctx.options.oximy_config) if ctx.options.oximy_config else None)
        self._output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = TraceWriter(self._output_dir, output_config["output"].get("filename_pattern", "traces_{date}.jsonl"))

        # Debug traces (unfiltered) - only if enabled
        if ctx.options.oximy_debug_traces:
            self._debug_writer = TraceWriter(self._output_dir, "all_traces_{date}.jsonl")
            logger.info("Debug traces enabled: logging all requests to all_traces_{date}.jsonl")
        else:
            self._debug_writer = None
        self._sensor_config_url = output_config.get("sensor_config_url", DEFAULT_SENSOR_CONFIG_URL)
        self._sensor_config_cache = output_config.get("sensor_config_cache", DEFAULT_SENSOR_CONFIG_CACHE)
        self._config_refresh_interval = output_config.get("config_refresh_interval_seconds", DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS)
        # Ensure output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Fetch sensor config from API (cached locally)
        sensor_config = fetch_sensor_config(self._sensor_config_url, self._sensor_config_cache)
        self._whitelist = sensor_config.get("whitelist", [])
        self._blacklist = sensor_config.get("blacklist", [])
        passthrough_patterns = sensor_config.get("passthrough", [])
        self._tls = TLSPassthrough(passthrough_patterns)

        # Hierarchical filtering config
        app_origins = sensor_config.get("allowed_app_origins", {})
        self._allowed_app_hosts = app_origins.get("hosts", [])
        self._allowed_app_non_hosts = app_origins.get("non_hosts", [])
        self._allowed_host_origins = sensor_config.get("allowed_host_origins", [])

        # Start periodic config refresh (only if not already running)
        if self._config_refresh_thread is None or not self._config_refresh_thread.is_alive():
            self._start_config_refresh_task()

        # Start background trigger file monitor
        self._start_force_sync_monitor()

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
        logger.info(
            f"===== OXIMY READY: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist, "
            f"{len(passthrough_patterns)} passthrough, {len(self._allowed_app_hosts)} app_hosts, "
            f"{len(self._allowed_host_origins)} host_origins ====="
        )

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

    def _extract_request_origin(self, flow: http.HTTPFlow) -> str | None:
        """Extract origin domain from request headers (Origin or Referer).

        Returns the domain portion of the Origin or Referer header.
        Used for host origin filtering to determine which website
        initiated the request.
        """
        # Try Origin header first (more reliable for cross-origin checks)
        origin_header = flow.request.headers.get("origin") or flow.request.headers.get("Origin")
        if origin_header:
            try:
                parsed = urlparse(origin_header)
                if parsed.netloc:
                    return parsed.netloc
            except Exception:
                pass

        # Fall back to Referer header
        referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if referer_header:
            try:
                parsed = urlparse(referer_header)
                if parsed.netloc:
                    return parsed.netloc
            except Exception:
                pass

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
            # logger.debug(f"PASSTHROUGH: {host}")

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
        """Check hierarchical filters on request.

        Filter hierarchy:
        1. App Origin Check (bundle_id based)
        2. Host Origin Check (for browser apps only)
        3. Standard Whitelist/Blacklist Filters
        """
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        logger.info(f">>> {flow.request.method} {url[:100]}")

        # Get config snapshot for thread-safe filtering
        config = self._get_config_snapshot()

        # =====================================================================
        # STEP 1: Resolve client process FIRST (needed for app origin check)
        # =====================================================================
        client_process: ClientProcess | None = None
        if self._resolver and flow.client_conn and flow.client_conn.peername:
            try:
                client_port = flow.client_conn.peername[1]
                client_process = await self._resolver.get_process_for_port(client_port)
                flow.metadata["oximy_client"] = client_process
                logger.debug(f"Client: {client_process.name} (PID {client_process.pid}, bundle: {client_process.bundle_id})")
            except Exception as e:
                logger.debug(f"Failed to get client process: {e}")

        # =====================================================================
        # STEP 2: App Origin Check (Layer 1)
        # =====================================================================
        bundle_id = client_process.bundle_id if client_process else None
        app_type = matches_app_origin(
            bundle_id,
            config["allowed_app_hosts"],
            config["allowed_app_non_hosts"],
        )

        if app_type is None:
            # App not in allowed list - skip capture
            logger.debug(f"[APP_SKIP] bundle_id={bundle_id} not in allowed apps")
            flow.metadata["oximy_skip"] = True
            flow.metadata["oximy_skip_reason"] = "app_not_allowed"
            return

        flow.metadata["oximy_app_type"] = app_type

        # =====================================================================
        # STEP 3: Host Origin Check (Layer 2) - only for "host" (browser) apps
        # =====================================================================
        if app_type == "host":
            request_origin = self._extract_request_origin(flow)

            if not matches_host_origin(request_origin, config["allowed_host_origins"]):
                logger.debug(f"[HOST_SKIP] origin={request_origin} not in allowed origins")
                flow.metadata["oximy_skip"] = True
                flow.metadata["oximy_skip_reason"] = "host_origin_not_allowed"
                return

            flow.metadata["oximy_host_origin"] = request_origin

        # =====================================================================
        # STEP 4: Standard Filters (Layer 3)
        # =====================================================================

        # Whitelist check (supports domain-only and domain+path patterns)
        if not matches_whitelist(host, path, config["whitelist"]):
            flow.metadata["oximy_skip"] = True
            flow.metadata["oximy_skip_reason"] = "not_whitelisted"
            return

        # Blacklist check on URL
        if word := self._check_blacklist(url, blacklist=config["blacklist"]):
            logger.info(f"[BLACKLISTED] {url[:80]} (matched: {word})")
            flow.metadata["oximy_skip"] = True
            flow.metadata["oximy_skip_reason"] = "blacklisted"
            return

        # GraphQL operation name blacklist check
        # For /graphql endpoints, also check the operationName in request body
        if path.endswith('/graphql') or '/graphql' in path:
            operation_name = extract_graphql_operation(flow.request.content)
            if operation_name:
                flow.metadata["oximy_graphql_op"] = operation_name
                if word := self._check_blacklist(operation_name, blacklist=config["blacklist"]):
                    logger.info(f"[BLACKLISTED_GRAPHQL] {operation_name} (matched: {word})")
                    flow.metadata["oximy_skip"] = True
                    flow.metadata["oximy_skip_reason"] = "blacklisted_graphql"
                    return

        # =====================================================================
        # Mark for capture
        # =====================================================================
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_start"] = time.time()
        logger.debug(f"[CAPTURE] {url[:80]} (app_type={app_type})")

    def response(self, flow: http.HTTPFlow) -> None:
        """Write trace for captured response."""
        if not self._enabled:
            return

        if not flow.response:
            return

        # Handle WebSocket upgrade (101 Switching Protocols) separately
        if flow.response.status_code == 101:
            logger.info(f"[101_DETECTED] {flow.request.pretty_host}{flow.request.path} - flow.websocket={flow.websocket is not None}")
            self._handle_websocket_upgrade(flow)
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        content_type = flow.response.headers.get("content-type", "")
        response_body = normalize_body(flow.response.content, content_type)
        event = self._build_event(flow, response_body)

        # Always write to debug log (unfiltered)
        if self._debug_writer:
            self._debug_writer.write(event)

        # Only write to main traces if not skipped by whitelist/blacklist
        if flow.metadata.get("oximy_skip"):
            return

        if self._writer:
            self._writer.write(event)
            self._traces_since_upload += 1
            graphql_op = flow.metadata.get("oximy_graphql_op", "")
            op_suffix = f" op={graphql_op}" if graphql_op else ""
            logger.info(f"<<< CAPTURED: {flow.request.method} {url[:80]} [{flow.response.status_code}]{op_suffix}")

            # Check if we should upload
            self._maybe_upload()

    def _handle_websocket_upgrade(self, flow: http.HTTPFlow) -> None:
        """Handle WebSocket upgrade (101 Switching Protocols) response."""
        # Skip if marked to skip by filters
        if flow.metadata.get("oximy_skip"):
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Build upgrade event (101 response)
        event = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket_upgrade",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info
        client_info: dict | None = None
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")
        if client_process:
            client_info = {
                "pid": client_process.pid,
                "bundle_id": client_process.bundle_id,
            }
            if client_process.name:
                client_info["name"] = client_process.name

            # Add hierarchical filter metadata
            if flow.metadata.get("oximy_app_type"):
                client_info["app_type"] = flow.metadata["oximy_app_type"]
            if flow.metadata.get("oximy_host_origin"):
                client_info["host_origin"] = flow.metadata["oximy_host_origin"]

            event["client"] = client_info

        # Extract referrer origin from headers
        referrer_origin: str | None = None
        referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if referer_header:
            try:
                parsed = urlparse(referer_header)
                if parsed.netloc:
                    referrer_origin = parsed.netloc
            except Exception:
                pass

        if referrer_origin and client_info:
            client_info["referrer_origin"] = referrer_origin

        # Filter out cookie headers for privacy
        request_headers = {k: v for k, v in flow.request.headers.items() if k.lower() != "cookie"}
        response_headers = {k: v for k, v in flow.response.headers.items() if k.lower() != "set-cookie"} if flow.response else {}

        # Add request/response info
        event["request"] = {
            "method": flow.request.method,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "headers": request_headers,
        }
        event["response"] = {
            "status_code": flow.response.status_code if flow.response else 101,
            "headers": response_headers,
        }

        # Always write to debug log (unfiltered)
        if self._debug_writer:
            self._debug_writer.write(event)

        if self._writer:
            self._writer.write(event)
            self._traces_since_upload += 1
            logger.info(f"<<< CAPTURED WS_UPGRADE: {flow.request.method} {url[:80]} [101]")

            # Check if we should upload
            self._maybe_upload()

    def _is_ws_turn_complete(self, content: str) -> bool:
        """Detect if a WebSocket message signals end of a conversation turn.

        Checks for common completion patterns across streaming/RPC protocols:
        - event/type fields with done/end/complete/message_stop values
        - finished/done/complete boolean fields set to true
        - OpenAI-style "[DONE]" marker
        - RPC-style response completion (ok/status fields with final payload)
        - Control flags indicating stream end (common in multiplexed protocols)
        - Nested payload completion patterns
        """
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return False

            # Skip heartbeat/ping/ack-only messages - these aren't turn completions
            msg_type = str(data.get("type", "")).lower()
            if msg_type in ("ping", "pong", "heartbeat", "ack"):
                return False

            # Check if streamId is "heartbeat" - skip these
            if str(data.get("streamId", "")).lower() == "heartbeat":
                return False

            # =================================================================
            # Pattern 1: Explicit completion type/event values
            # =================================================================
            completion_values = {"done", "end", "complete", "message_stop", "finished", "stop", "final"}
            for field in ("event", "type"):
                if str(data.get(field, "")).lower() in completion_values:
                    return True

            # =================================================================
            # Pattern 2: Boolean completion flags
            # =================================================================
            for field in ("finished", "done", "complete", "is_finished", "is_final", "is_done"):
                if data.get(field) is True:
                    return True

            # =================================================================
            # Pattern 3: OpenAI-style "[DONE]" marker
            # =================================================================
            if data.get("data") == "[DONE]":
                return True

            # =================================================================
            # Pattern 4: RPC-style response completion
            # Many RPC-over-WebSocket protocols send {ok: true, payload: {...}}
            # or {status: "ok", result: {...}} for completed responses
            # =================================================================
            payload = data.get("payload")
            if isinstance(payload, dict):
                # Check for nested ok/status indicating RPC response completion
                if payload.get("ok") is True and "payload" in payload:
                    # This is a successful RPC response with final payload
                    # But we need to distinguish from intermediate streaming chunks
                    inner_payload = payload.get("payload")
                    if isinstance(inner_payload, dict):
                        # Check if the inner payload has completion indicators
                        inner_type = str(inner_payload.get("type", "")).lower()
                        if inner_type in completion_values:
                            return True
                        # Check for state/status fields indicating completion
                        if inner_payload.get("done") is True or inner_payload.get("finished") is True:
                            return True

                # Check nested type field for completion values
                payload_type = str(payload.get("type", "")).lower()
                if payload_type in completion_values:
                    return True

                # Check for status field in payload
                payload_status = str(payload.get("status", "")).lower()
                if payload_status in ("done", "complete", "finished", "success", "ok"):
                    return True

            # =================================================================
            # Pattern 5: Control flags indicating stream end
            # Common in multiplexed/RPC protocols (gRPC-web, custom RPC, etc.)
            # Typically: bit 0 = FIN, bit 1 = stream close, etc.
            # =================================================================
            control_flags = data.get("controlFlags")
            if isinstance(control_flags, int) and control_flags > 0:
                # Many protocols use specific flag values for stream termination
                # Common patterns:
                # - Odd flags (bit 0 set) often indicate control/fin messages
                # - Flag value 1, 2, 3 often indicate close/end
                # - Higher bits may indicate error vs normal close

                # Check for common "stream end" flag patterns
                # Be careful not to match ACK-only messages (often flag=1 with streamId="heartbeat")
                stream_id = data.get("streamId", "")

                # Flag patterns that typically indicate stream completion:
                # - controlFlags with FIN bit and a non-heartbeat stream
                # - controlFlags indicating "close stream" (varies by protocol)
                if stream_id and stream_id != "heartbeat":
                    # Check for FIN/close patterns in control flags
                    # Bit 1 (value 2) or bit 2 (value 4) often indicates stream end
                    # Combined with other bits for close (e.g., 2, 3, 6, 7)
                    stream_end_flags = {2, 3, 6, 7, 10, 11, 14, 15}  # Common close flag patterns
                    if control_flags in stream_end_flags:
                        return True

            # =================================================================
            # Pattern 6: Status/result field presence (generic RPC)
            # =================================================================
            status = data.get("status")
            if isinstance(status, dict):
                # Status object often indicates completion
                if status.get("ok") is True or status.get("code") == "OK":
                    return True

        except (json.JSONDecodeError, TypeError):
            pass
        return False

    def _write_ws_turn_aggregate(self, flow: http.HTTPFlow) -> None:
        """Write aggregate event for completed conversation turn."""
        ws_messages = flow.metadata.get("oximy_ws_messages", [])
        if not ws_messages:
            return

        host = flow.request.pretty_host
        path = flow.request.path

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket_turn",
        }

        if self._device_id:
            event["device_id"] = self._device_id

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

            # Add hierarchical filter metadata
            if flow.metadata.get("oximy_app_type"):
                client_info["app_type"] = flow.metadata["oximy_app_type"]
            if flow.metadata.get("oximy_host_origin"):
                client_info["host_origin"] = flow.metadata["oximy_host_origin"]

            # Extract referrer origin from headers
            referrer_origin: str | None = None
            referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
            if referer_header:
                try:
                    parsed = urlparse(referer_header)
                    if parsed.netloc:
                        referrer_origin = parsed.netloc
                except Exception:
                    pass

            if referrer_origin:
                client_info["referrer_origin"] = referrer_origin

            event["client"] = client_info

        # Add WebSocket-specific fields
        event["host"] = host
        event["path"] = path
        event["messages"] = ws_messages
        event["timing"] = {"message_count": len(ws_messages)}

        # Write to debug log (unfiltered)
        if self._debug_writer:
            self._debug_writer.write(event)

        # Write to main traces
        if self._writer:
            self._writer.write(event)
            self._traces_since_upload += 1
            logger.info(f"<<< CAPTURED WS_TURN: {host} ({len(ws_messages)} messages)")
            self._maybe_upload()

        # Clear buffer for next turn
        flow.metadata["oximy_ws_messages"] = []
        flow.metadata["oximy_ws_message_count"] = 0

    def _build_event(self, flow: http.HTTPFlow, response_body: str) -> dict:
        """Build trace event."""
        request_body = normalize_body(flow.request.content) if flow.request.content else None

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

        # Extract referrer origin from headers
        referrer_origin: str | None = None
        referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if referer_header:
            try:
                parsed = urlparse(referer_header)
                if parsed.netloc:
                    referrer_origin = parsed.netloc
            except Exception:
                pass

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "http",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info
        if client_info:
            if referrer_origin:
                client_info["referrer_origin"] = referrer_origin

            # Add hierarchical filter metadata
            if flow.metadata.get("oximy_app_type"):
                client_info["app_type"] = flow.metadata["oximy_app_type"]
            if flow.metadata.get("oximy_host_origin"):
                client_info["host_origin"] = flow.metadata["oximy_host_origin"]

            event["client"] = client_info

        # Add request/response/timing
        request_data = {
            "method": flow.request.method,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "headers": request_headers,
            "body": request_body,
        }
        # Include GraphQL operation name if present
        if graphql_op := flow.metadata.get("oximy_graphql_op"):
            request_data["graphql_operation"] = graphql_op
        event["request"] = request_data
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

    def websocket_start(self, flow: http.HTTPFlow) -> None:
        """Called when WebSocket connection is established."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        logger.info(f"[WS_START] {host}{path} - WebSocket connection established, flow.websocket={flow.websocket is not None}")

        # Initialize message tracking in metadata
        flow.metadata["oximy_ws_messages"] = []
        flow.metadata["oximy_ws_start"] = time.time()
        flow.metadata["oximy_ws_message_count"] = 0

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Capture WebSocket messages in real-time."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Skip if marked by filters (should have been set in request hook)
        if flow.metadata.get("oximy_skip"):
            return

        # Ensure we have WebSocket messages to process
        if not flow.websocket or not flow.websocket.messages:
            logger.warning(f"[WS_MESSAGE] {url} - called but no websocket messages found")
            return

        # Get the last message (the new one that triggered this hook)
        msg = flow.websocket.messages[-1]

        # Check message direction and content
        direction = "client" if msg.from_client else "server"
        is_text = hasattr(msg, 'is_text') and msg.is_text
        content = normalize_body(msg.content) if isinstance(msg.content, bytes) else str(msg.content)

        logger.info(f"[WS_MESSAGE] {url} - {direction} message (text={is_text}, size={len(content)} chars)")

        # Accumulate message with deduplication tracking
        current_count = len(flow.websocket.messages)
        last_processed = flow.metadata.get("oximy_ws_message_count", 0)

        # Only process messages we haven't processed yet
        if current_count > last_processed:
            message_data = {
                "direction": direction,
                "timestamp": datetime.fromtimestamp(msg.timestamp, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "content": content,
                "is_text": is_text,
            }

            # Accumulate for aggregate events
            if "oximy_ws_messages" not in flow.metadata:
                flow.metadata["oximy_ws_messages"] = []
            flow.metadata["oximy_ws_messages"].append(message_data)
            flow.metadata["oximy_ws_message_count"] = current_count

            logger.info(f"[WS_MESSAGE_CAPTURED] {url} - message #{current_count} from {direction}: {content[:100]}")

            # Check for completion signals in server messages and write aggregate
            if not msg.from_client and self._is_ws_turn_complete(content):
                logger.info(f"[WS_TURN_COMPLETE] {url} - detected completion signal, writing aggregate")
                self._write_ws_turn_aggregate(flow)

    def websocket_end(self, flow: http.HTTPFlow) -> None:
        """Write WebSocket trace on connection close."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Try to get messages from flow.websocket.messages directly (mitmproxy stores them)
        ws_messages = []
        if flow.websocket and flow.websocket.messages:
            logger.info(f"[WS_END] {url} - found {len(flow.websocket.messages)} messages in flow.websocket")
            for msg in flow.websocket.messages:
                try:
                    content = normalize_body(msg.content) if isinstance(msg.content, bytes) else str(msg.content)
                    ws_messages.append({
                        "direction": "client" if msg.from_client else "server",
                        "timestamp": datetime.fromtimestamp(msg.timestamp, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "content": content,
                    })
                except Exception as e:
                    logger.warning(f"Failed to process websocket message: {e}")

        # Fallback to metadata if available
        if not ws_messages:
            ws_messages = flow.metadata.get("oximy_ws_messages", [])

        logger.info(f"[WS_END] {host}{path} - connection closed, accumulated {len(ws_messages)} messages")

        if not ws_messages:
            logger.info(f"[WS_END_SKIP] {host}{path} - no messages to write")
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

        # Extract referrer origin from headers
        referrer_origin: str | None = None
        referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if referer_header:
            try:
                parsed = urlparse(referer_header)
                if parsed.netloc:
                    referrer_origin = parsed.netloc
            except Exception:
                pass

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info
        if client_info:
            if referrer_origin:
                client_info["referrer_origin"] = referrer_origin

            # Add hierarchical filter metadata
            if flow.metadata.get("oximy_app_type"):
                client_info["app_type"] = flow.metadata["oximy_app_type"]
            if flow.metadata.get("oximy_host_origin"):
                client_info["host_origin"] = flow.metadata["oximy_host_origin"]

            event["client"] = client_info

        # Add WebSocket-specific fields
        event["host"] = flow.request.pretty_host
        event["path"] = flow.request.path
        event["messages"] = ws_messages
        event["timing"] = {"duration_ms": int((time.time() - start) * 1000), "message_count": len(ws_messages)}

        # Always write to debug log (unfiltered)
        if self._debug_writer:
            self._debug_writer.write(event)

        # Only write to main traces if not skipped by whitelist/blacklist
        if flow.metadata.get("oximy_skip"):
            return

        if self._writer:
            self._writer.write(event)
            self._traces_since_upload += 1
            logger.info(f"<<< CAPTURED WS: {flow.request.pretty_host} ({len(ws_messages)} messages)")

            # Check if we should upload
            self._maybe_upload()

    # =========================================================================
    # Upload Trigger
    # =========================================================================

    def _maybe_upload(self) -> None:
        """Upload traces if threshold reached (100 traces or 2 seconds elapsed)."""
        if not self._uploader or not self._output_dir:
            return

        now = time.time()
        time_elapsed = now - self._last_upload_time >= UPLOAD_INTERVAL_SECONDS
        count_reached = self._traces_since_upload >= UPLOAD_THRESHOLD_COUNT

        if (time_elapsed or count_reached) and self._traces_since_upload > 0:
            try:
                if self._writer and self._writer._fo:
                    self._writer._fo.flush()

                uploaded = self._uploader.upload_all_pending(self._output_dir)
                if uploaded > 0:
                    logger.info(f"Uploaded {uploaded} traces to API")

                self._last_upload_time = now
                self._traces_since_upload = 0
            except Exception as e:
                logger.warning(f"Failed to upload traces: {e}")

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

        # Close writers to flush pending writes
        if self._writer:
            self._writer.close()
            self._writer = None
        if self._debug_writer:
            self._debug_writer.close()
            self._debug_writer = None

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


addons = [
    OximyAddon(),
]
