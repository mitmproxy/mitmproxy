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
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import IO

from mitmproxy import ctx, http, tls

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
    import subprocess
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
    import subprocess

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
        return True  # Skip check on non-macOS

    import subprocess
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

    import subprocess
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

def load_json_list(path: Path, key: str) -> list[str]:
    """Load a list from a JSON file."""
    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get(key, [])
        logger.info(f"Loaded {len(items)} {key} from {path.name}")
        return items
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load {path}: {e}")
        return []


def load_config(config_path: Path | None = None) -> dict:
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

class TLSPassthrough:
    """Manages TLS passthrough for certificate-pinned hosts."""

    def __init__(self, passthrough_path: Path):
        self._path = passthrough_path
        self._patterns: list[re.Pattern] = []
        self._reload()

    def _reload(self) -> None:
        """Load patterns from passthrough.json."""
        patterns = load_json_list(self._path, "patterns")
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def should_passthrough(self, host: str) -> bool:
        """Check if host should bypass TLS interception."""
        return any(p.match(host) for p in self._patterns)

    def add_host(self, host: str) -> None:
        """Add a host to passthrough.json."""
        try:
            if self._path.exists():
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"patterns": []}

            # Add as exact match pattern
            pattern = f"^{re.escape(host)}$"
            if pattern not in data["patterns"]:
                data["patterns"].append(pattern)
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                self._reload()
                logger.info(f"Added to passthrough: {host}")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to update passthrough.json: {e}")

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

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option("oximy_enabled", bool, False, "Enable AI traffic capture")
        loader.add_option("oximy_config", str, "", "Path to config.json")
        loader.add_option("oximy_output_dir", str, "~/.oximy/traces", "Output directory")
        loader.add_option("oximy_verbose", bool, False, "Verbose logging")

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

        addon_dir = Path(__file__).parent
        self._whitelist = load_json_list(addon_dir / "whitelist.json", "domains")
        self._blacklist = load_json_list(addon_dir / "blacklist.json", "words")
        self._tls = TLSPassthrough(addon_dir / "passthrough.json")

        config = load_config(Path(ctx.options.oximy_config) if ctx.options.oximy_config else None)
        output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = TraceWriter(output_dir, config["output"].get("filename_pattern", "traces_{date}.jsonl"))

        _set_system_proxy(enable=True)
        logger.info(f"===== OXIMY READY: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist =====")

    def _check_blacklist(self, *texts: str) -> str | None:
        """Check if any text contains a blacklisted word."""
        for text in texts:
            if word := contains_blacklist_word(text, self._blacklist):
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

    def request(self, flow: http.HTTPFlow) -> None:
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

        # Blacklist check on URL and request body
        request_body = ""
        if flow.request.content:
            try:
                request_body = flow.request.content.decode("utf-8", errors="replace")
            except Exception:
                pass

        if word := self._check_blacklist(url, request_body):
            logger.info(f"[BLACKLISTED] {url[:80]} (matched: {word})")
            flow.metadata["oximy_skip"] = True
            return

        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_start"] = time.time()

    def response(self, flow: http.HTTPFlow) -> None:
        """Check blacklist on response and write trace."""
        if not self._enabled or not self._writer:
            return

        if flow.metadata.get("oximy_skip") or flow.websocket:
            return

        if not flow.response:
            return

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Blacklist check on response body
        response_body = ""
        if flow.response.content:
            try:
                response_body = flow.response.content.decode("utf-8", errors="replace")
            except Exception:
                pass

        if word := self._check_blacklist(response_body):
            logger.info(f"[BLACKLISTED] {url[:80]} (response matched: {word})")
            return

        # Build and write event
        event = self._build_event(flow, response_body)
        self._writer.write(event)
        logger.info(f"<<< CAPTURED: {flow.request.method} {url[:80]} [{flow.response.status_code}]")

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

        return {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "http",
            "request": {
                "method": flow.request.method,
                "host": flow.request.pretty_host,
                "path": flow.request.path,
                "headers": dict(flow.request.headers),
                "body": request_body,
            },
            "response": {
                "status_code": flow.response.status_code if flow.response else None,
                "headers": dict(flow.response.headers) if flow.response else {},
                "body": response_body if response_body else None,
            },
            "timing": {"duration_ms": duration_ms, "ttfb_ms": ttfb_ms},
        }

    # =========================================================================
    # WebSocket Hooks
    # =========================================================================

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Accumulate WebSocket messages."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        if not matches_domain(host, self._whitelist):
            flow.metadata["oximy_skip"] = True
            return

        if "oximy_ws_messages" not in flow.metadata:
            flow.metadata["oximy_ws_messages"] = []
            flow.metadata["oximy_ws_start"] = time.time()

        if flow.websocket and flow.websocket.messages:
            msg = flow.websocket.messages[-1]
            content = msg.content.decode("utf-8", errors="replace") if isinstance(msg.content, bytes) else str(msg.content)

            # Blacklist check on message content
            if word := self._check_blacklist(content):
                logger.info(f"[BLACKLISTED] WS {host} (message matched: {word})")
                return

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
        event = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket",
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "messages": messages,
            "timing": {"duration_ms": int((time.time() - start) * 1000), "message_count": len(messages)},
        }
        self._writer.write(event)
        logger.info(f"<<< CAPTURED WS: {flow.request.pretty_host} ({len(messages)} messages)")

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
        _set_system_proxy(enable=False)
        if self._writer:
            self._writer.close()
            self._writer = None
        self._enabled = False
        logger.info("Oximy addon disabled")


addons = [OximyAddon()]
