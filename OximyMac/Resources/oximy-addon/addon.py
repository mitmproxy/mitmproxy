"""
Lightweight Oximy addon for mitmproxy.

Captures AI API traffic with whitelist/blacklist filtering.
Supports: HTTP/REST, SSE, WebSocket, HTTP/2, HTTP/3, gRPC

No parsing or normalization - saves raw request/response bodies to JSONL.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import os
import platform
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import IO

from mitmproxy import ctx, http, tls

# Configure logging to output to stderr
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# System proxy settings
PROXY_HOST = "127.0.0.1"
PROXY_PORT = "8080"
NETWORK_SERVICE = "Wi-Fi"  # macOS network interface


# =============================================================================
# SYSTEM PROXY CONFIGURATION
# =============================================================================

def _set_system_proxy(enable: bool) -> None:
    """Enable or disable system proxy settings (cross-platform)."""
    if sys.platform == "darwin":
        _set_macos_proxy(enable)
    elif sys.platform == "win32":
        _set_windows_proxy(enable)
    else:
        logger.debug("Auto proxy configuration not supported on this platform")


def _set_windows_proxy(enable: bool) -> None:
    """Enable or disable Windows system proxy settings via registry."""
    import subprocess
    proxy_server = f"{PROXY_HOST}:{PROXY_PORT}"

    try:
        if enable:
            # Enable proxy via reg command
            subprocess.run([
                "reg", "add",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "1", "/f"
            ], check=True, capture_output=True)
            subprocess.run([
                "reg", "add",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "/v", "ProxyServer", "/t", "REG_SZ", "/d", proxy_server, "/f"
            ], check=True, capture_output=True)
            logger.info(f"Windows system proxy enabled: {proxy_server}")
        else:
            subprocess.run([
                "reg", "add",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "0", "/f"
            ], check=True, capture_output=True)
            logger.info("Windows system proxy disabled")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to set Windows proxy: {e}")


def _set_macos_proxy(enable: bool) -> None:
    """Enable or disable macOS system proxy settings."""
    import subprocess

    try:
        if enable:
            # Enable HTTPS proxy
            subprocess.run([
                "networksetup", "-setsecurewebproxy",
                NETWORK_SERVICE, PROXY_HOST, PROXY_PORT,
            ], check=True, capture_output=True)
            # Enable HTTP proxy
            subprocess.run([
                "networksetup", "-setwebproxy",
                NETWORK_SERVICE, PROXY_HOST, PROXY_PORT,
            ], check=True, capture_output=True)
            logger.info(f"macOS system proxy enabled: {PROXY_HOST}:{PROXY_PORT}")
        else:
            # Disable HTTPS proxy
            subprocess.run([
                "networksetup", "-setsecurewebproxystate",
                NETWORK_SERVICE, "off",
            ], check=True, capture_output=True)
            # Disable HTTP proxy
            subprocess.run([
                "networksetup", "-setwebproxystate",
                NETWORK_SERVICE, "off",
            ], check=True, capture_output=True)
            logger.info("macOS system proxy disabled")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to {'enable' if enable else 'disable'} macOS system proxy: {e}")
    except FileNotFoundError:
        logger.warning("networksetup command not found - not on macOS?")


def load_whitelist(whitelist_path: Path) -> list[str]:
    """Load whitelist domains from JSON file."""
    if not whitelist_path.exists():
        logger.error(f"Whitelist file not found: {whitelist_path}")
        return []

    try:
        with open(whitelist_path, encoding="utf-8") as f:
            data = json.load(f)
        domains = data.get("domains", [])
        logger.info(f"Loaded {len(domains)} domains from {whitelist_path}")
        return domains
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load whitelist from {whitelist_path}: {e}")
        return []


def load_blacklist(blacklist_path: Path) -> list[str]:
    """Load blacklist words from JSON file."""
    if not blacklist_path.exists():
        logger.error(f"Blacklist file not found: {blacklist_path}")
        return []

    try:
        with open(blacklist_path, encoding="utf-8") as f:
            data = json.load(f)
        words = data.get("words", [])
        logger.info(f"Loaded {len(words)} blacklist words from {blacklist_path}")
        return words
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load blacklist from {blacklist_path}: {e}")
        return []


def load_passthrough_patterns(passthrough_path: Path) -> list[str]:
    """Load TLS passthrough patterns from JSON file."""
    if not passthrough_path.exists():
        logger.warning(f"Passthrough file not found: {passthrough_path}")
        return []

    try:
        with open(passthrough_path, encoding="utf-8") as f:
            data = json.load(f)
        patterns = data.get("patterns", [])
        logger.info(f"Loaded {len(patterns)} passthrough patterns from {passthrough_path}")
        return patterns
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load passthrough from {passthrough_path}: {e}")
        return []


def load_config(config_path: Path | None = None) -> dict:
    """Load output configuration from JSON file with fallback to defaults."""
    default_config = {
        "output": {
            "directory": "~/.oximy/traces",
            "filename_pattern": "traces_{date}.jsonl",
        },
    }

    if config_path and config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                user_config = json.load(f)
            if "output" in user_config:
                default_config["output"].update(user_config["output"])
            logger.info(f"Loaded config from {config_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")

    return default_config


# =============================================================================
# DOMAIN MATCHING
# =============================================================================

def matches_domain(host: str, patterns: list[str]) -> str | None:
    """
    Check if host matches any pattern in the whitelist.
    Returns the matched pattern, or None if no match.
    Supports wildcards like *.openai.com and regex patterns like bedrock-runtime.*.amazonaws.com
    """
    host_lower = host.lower()

    for pattern in patterns:
        pattern_lower = pattern.lower()

        # Exact match
        if host_lower == pattern_lower:
            return pattern

        # Wildcard prefix match (*.example.com)
        if pattern_lower.startswith("*."):
            suffix = pattern_lower[1:]  # .example.com
            if host_lower.endswith(suffix) or host_lower == pattern_lower[2:]:
                return pattern

        # fnmatch for more complex patterns
        if fnmatch.fnmatch(host_lower, pattern_lower):
            return pattern

        # Regex pattern for patterns like bedrock-runtime.*.amazonaws.com
        if "*" in pattern and not pattern.startswith("*"):
            regex_pattern = pattern_lower.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{regex_pattern}$", host_lower):
                return pattern

    return None


def contains_blacklist_word(url: str, words: list[str]) -> bool:
    """Check if URL contains any blacklisted word."""
    url_lower = url.lower()
    return any(word.lower() in url_lower for word in words)


# =============================================================================
# TLS PASSTHROUGH
# =============================================================================

class TLSPassthrough:
    """
    Manages TLS passthrough for certificate-pinned hosts.

    - Skips interception for known pinned hosts (Apple, Google, etc.)
    - Auto-learns new pinned hosts from TLS failures
    - Persists learned hosts across restarts
    """

    def __init__(self, patterns: list[str], persist_path: Path | None = None):
        self._known_patterns: list[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in patterns
        ]
        self._learned_hosts: set[str] = set()
        self._persist_path = persist_path

        # Load persisted hosts
        if persist_path:
            self._load_persisted()

    def should_passthrough(self, host: str) -> tuple[bool, str | None]:
        """Check if a host should bypass TLS interception."""
        # Check known patterns first
        for pattern in self._known_patterns:
            if pattern.match(host):
                return True, "known_pinned"

        # Check learned hosts
        if host in self._learned_hosts:
            return True, "learned_pinned"

        return False, None

    def record_tls_failure(self, host: str, error: str) -> bool:
        """
        Record a TLS handshake failure and determine if it's certificate pinning.
        Returns True if this was likely certificate pinning.
        """
        # Patterns that indicate certificate pinning
        pinning_indicators = [
            "certificate verify failed",
            "unknown ca",
            "bad certificate",
            "certificate_unknown",
            "self signed certificate",
            "unable to get local issuer certificate",
            "client disconnected during the handshake",
            "does not trust the proxy's certificate",
        ]

        error_lower = error.lower()
        is_pinning = any(indicator in error_lower for indicator in pinning_indicators)

        if is_pinning and host not in self._learned_hosts:
            self._learned_hosts.add(host)
            self._persist()
            logger.info(f"Certificate pinning detected: {host} - added to passthrough list")
            return True

        return False

    def _load_persisted(self) -> None:
        """Load learned hosts from persistence file."""
        if not self._persist_path or not self._persist_path.exists():
            return

        try:
            data = json.loads(self._persist_path.read_text())
            self._learned_hosts = set(data.get("learned_hosts", []))
            if self._learned_hosts:
                logger.info(f"Loaded {len(self._learned_hosts)} learned pinned hosts from cache")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load persisted hosts: {e}")

    def _persist(self) -> None:
        """Save learned hosts to persistence file."""
        if not self._persist_path:
            return

        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps({"learned_hosts": sorted(self._learned_hosts)}, indent=2)
            )
        except OSError as e:
            logger.warning(f"Failed to persist learned hosts: {e}")

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """
        Called when a TLS ClientHello is received.
        If the host is known to be pinned, skip interception immediately.
        """
        server = data.context.server
        host = data.client_hello.sni or (server.address[0] if server.address else None)

        if not host:
            return

        should_pass, reason = self.should_passthrough(host)

        if should_pass:
            data.ignore_connection = True
            logger.debug(f"TLS passthrough ({reason}): {host}")

    def tls_failed_client(self, data: tls.TlsData) -> None:
        """
        Called when TLS handshake with client fails.
        Records the failure to learn certificate-pinned hosts.
        """
        server = data.context.server
        host = server.sni or (server.address[0] if server.address else None)

        if not host:
            return

        error = str(data.conn.error) if data.conn.error else "unknown error"
        self.record_tls_failure(host, error)


# =============================================================================
# PROCESS ATTRIBUTION
# =============================================================================

@dataclass
class ClientProcess:
    """Information about the client process that made a request."""

    pid: int | None
    name: str | None
    path: str | None
    ppid: int | None
    parent_name: str | None
    user: str | None
    port: int
    bundle_id: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        result: dict = {"port": self.port}
        if self.pid is not None:
            result["pid"] = self.pid
        if self.name is not None:
            result["name"] = self.name
        if self.path is not None:
            result["path"] = self.path
        if self.ppid is not None:
            result["ppid"] = self.ppid
        if self.parent_name is not None:
            result["parent_name"] = self.parent_name
        if self.user is not None:
            result["user"] = self.user
        if self.bundle_id is not None:
            result["bundle_id"] = self.bundle_id
        return result


class ProcessResolver:
    """
    Resolves network connections to originating processes.
    Uses lsof on macOS/Linux and netstat on Windows.
    """

    def __init__(self):
        self._cache: dict[int, dict] = {}
        self._bundle_id_cache: dict[str, str | None] = {}
        self._is_macos = platform.system() == "Darwin"
        self._is_linux = platform.system() == "Linux"
        self._is_windows = platform.system() == "Windows"

    async def get_process_for_port(self, port: int) -> ClientProcess:
        """Get process information for a connection on the given local port."""
        if not (self._is_macos or self._is_linux or self._is_windows):
            return ClientProcess(
                pid=None, name="Unknown (unsupported platform)", path=None,
                ppid=None, parent_name=None, user=None, port=port, bundle_id=None,
            )

        # Find PID that owns this port
        pid = await self._find_pid_for_port(port)
        if pid is None:
            return ClientProcess(
                pid=None, name="Unknown (exited)", path=None,
                ppid=None, parent_name=None, user=None, port=port, bundle_id=None,
            )

        # Get process info
        proc_info = await self._get_process_info(pid)
        if proc_info is None:
            return ClientProcess(
                pid=pid, name="Unknown (exited)", path=None,
                ppid=None, parent_name=None, user=None, port=port, bundle_id=None,
            )

        # Get parent info
        parent_name = None
        if proc_info.get("ppid") and proc_info["ppid"] > 1:
            parent_info = await self._get_process_info(proc_info["ppid"])
            if parent_info:
                parent_name = self._extract_name(parent_info.get("path"))

        name = self._extract_name(proc_info.get("path"))
        bundle_id = await self._extract_bundle_id(proc_info.get("path"))

        return ClientProcess(
            pid=pid,
            name=name,
            path=proc_info.get("path"),
            ppid=proc_info.get("ppid"),
            parent_name=parent_name,
            user=proc_info.get("user"),
            port=port,
            bundle_id=bundle_id,
        )

    async def _find_pid_for_port(self, port: int) -> int | None:
        """Find the PID that owns a local port as the SOURCE (client side)."""
        if self._is_windows:
            return await self._find_pid_for_port_windows(port)

        try:
            proc = await asyncio.create_subprocess_exec(
                "lsof", "-i", f"TCP:{port}", "-n", "-P",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return None

            if proc.returncode == 0:
                for line in stdout.decode().strip().split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 9:
                        for field in [parts[-1], parts[-2]]:
                            if f":{port}->" in field:
                                return int(parts[1])
        except (ValueError, OSError) as e:
            logger.debug(f"Failed to find PID for port {port}: {e}")

        return None

    async def _find_pid_for_port_windows(self, port: int) -> int | None:
        """Find the PID that owns a local port on Windows using netstat."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "netstat", "-aon",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return None

            if proc.returncode == 0:
                for line in stdout.decode().strip().split("\n"):
                    if not line.strip() or "Proto" in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 5 and parts[0] == "TCP":
                        local_addr = parts[1]
                        if local_addr.endswith(f":{port}"):
                            try:
                                return int(parts[4])
                            except ValueError:
                                continue
        except (ValueError, OSError) as e:
            logger.debug(f"Failed to find PID for port {port} on Windows: {e}")

        return None

    async def _get_process_info(self, pid: int) -> dict | None:
        """Get process information for a PID, using cache if available."""
        if pid in self._cache:
            return self._cache[pid]

        info = await self._fetch_process_info(pid)
        if info:
            self._cache[pid] = info

        return info

    async def _fetch_process_info(self, pid: int) -> dict | None:
        """Fetch process info from the system."""
        if self._is_windows:
            return await self._fetch_process_info_windows(pid)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ps", "-p", str(pid), "-o", "pid=,ppid=,user=,comm=",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return None

            if proc.returncode == 0 and stdout.strip():
                parts = stdout.decode().strip().split(None, 3)
                if len(parts) >= 4:
                    return {
                        "pid": int(parts[0]),
                        "ppid": int(parts[1]),
                        "user": parts[2],
                        "path": parts[3],
                    }
        except (ValueError, OSError) as e:
            logger.debug(f"Failed to get process info for PID {pid}: {e}")

        return None

    async def _fetch_process_info_windows(self, pid: int) -> dict | None:
        """Fetch process info on Windows using wmic."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "wmic", "process", "where", f"processid={pid}",
                "get", "name,executablepath,parentprocessid",
                "/format:csv",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return None

            if proc.returncode == 0 and stdout.strip():
                lines = stdout.decode().strip().split("\n")
                for line in lines:
                    if not line.strip() or line.startswith("Node"):
                        continue
                    parts = line.strip().split(",")
                    if len(parts) >= 4:
                        exe_path = parts[1] if parts[1] else None
                        name = parts[2] if parts[2] else None
                        try:
                            ppid = int(parts[3]) if parts[3] else None
                        except ValueError:
                            ppid = None
                        return {
                            "pid": pid,
                            "ppid": ppid,
                            "user": None,
                            "path": exe_path or name,
                        }
        except (ValueError, OSError) as e:
            logger.debug(f"Failed to get process info for PID {pid} on Windows: {e}")

        return None

    def _extract_name(self, path: str | None) -> str | None:
        """Extract a readable process name from a path."""
        if not path:
            return None

        if "\\" in path:
            name = path.rsplit("\\", 1)[-1]
        else:
            name = path.rsplit("/", 1)[-1]

        if name.lower().endswith(".exe"):
            name = name[:-4]

        return name if name else None

    async def _extract_bundle_id(self, path: str | None) -> str | None:
        """Extract macOS bundle identifier from an app path."""
        if not path or not self._is_macos:
            return None

        if ".app" not in path:
            return None

        try:
            app_path = path.split(".app")[0] + ".app"

            if app_path in self._bundle_id_cache:
                return self._bundle_id_cache[app_path]

            plist_path = f"{app_path}/Contents/Info.plist"

            proc = await asyncio.create_subprocess_exec(
                "defaults", "read", plist_path, "CFBundleIdentifier",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                self._bundle_id_cache[app_path] = None
                return None

            if proc.returncode == 0 and stdout.strip():
                bundle_id = stdout.decode().strip()
                self._bundle_id_cache[app_path] = bundle_id
                return bundle_id

            self._bundle_id_cache[app_path] = None

        except OSError as e:
            logger.debug(f"Failed to extract bundle_id from {path}: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear the process info cache."""
        self._cache.clear()
        self._bundle_id_cache.clear()


# =============================================================================
# EVENT WRITER
# =============================================================================

class TraceWriter:
    """
    Writes trace events to rotating JSONL files.
    Files are rotated daily with naming pattern: traces_YYYY-MM-DD.jsonl
    """

    def __init__(
        self,
        output_dir: Path | str,
        filename_pattern: str = "traces_{date}.jsonl",
    ):
        self.output_dir = Path(output_dir).expanduser()
        self.filename_pattern = filename_pattern
        self._current_file: Path | None = None
        self._fo: IO[str] | None = None
        self._event_count: int = 0

    def write(self, event: dict) -> None:
        """Write an event to the current JSONL file."""
        self._maybe_rotate()

        if self._fo is None:
            logger.error("No file handle available for writing")
            return

        try:
            line = json.dumps(event, separators=(",", ":"))
            self._fo.write(line + "\n")
            self._fo.flush()  # Force flush to disk
            self._event_count += 1
            logger.info(f"Wrote event {self._event_count} to {self._current_file}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to write event: {e}")

    def _maybe_rotate(self) -> None:
        """Rotate to a new file if the date has changed."""
        expected_file = self._get_current_filepath()

        if self._current_file == expected_file:
            return

        if self._fo is not None:
            try:
                self._fo.close()
            except IOError:
                pass
            self._fo = None

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create output directory: {e}")
            return

        try:
            self._fo = open(expected_file, "a", encoding="utf-8", buffering=1)
            self._current_file = expected_file
            logger.info(f"Opened trace file: {expected_file}")
        except IOError as e:
            logger.error(f"Failed to open trace file: {e}")

    def _get_current_filepath(self) -> Path:
        """Get the filepath for the current date."""
        today = date.today().isoformat()
        filename = self.filename_pattern.format(date=today)
        return self.output_dir / filename

    def close(self) -> None:
        """Close the current file handle."""
        if self._fo is not None:
            try:
                self._fo.close()
                logger.info(f"Closed trace file (wrote {self._event_count} events)")
            except IOError as e:
                logger.error(f"Failed to close trace file: {e}")
            finally:
                self._fo = None
                self._current_file = None

    @property
    def event_count(self) -> int:
        """Get the total number of events written."""
        return self._event_count


# =============================================================================
# UUID v7 GENERATION
# =============================================================================

def generate_event_id() -> str:
    """
    Generate a UUID v7 (time-sortable).
    Format: 8-4-4-4-12 hex characters
    """
    # Get timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)

    # Get 12 bits of random
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF

    # Get 62 bits of random
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF

    # Construct UUID v7
    # timestamp_ms (48 bits) | version (4 bits) | rand_a (12 bits) | variant (2 bits) | rand_b (62 bits)
    uuid_int = (
        (timestamp_ms << 80) |
        (0x7 << 76) |  # version 7
        (rand_a << 64) |
        (0x2 << 62) |  # variant
        rand_b
    )

    # Format as UUID string
    hex_str = f"{uuid_int:032x}"
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


# =============================================================================
# MAIN ADDON
# =============================================================================

class OximyAddon:
    """
    Lightweight mitmproxy addon that captures AI API traffic.
    Uses whitelist/blacklist for filtering, saves raw bodies to JSONL.
    Supports HTTP/REST, SSE, WebSocket, HTTP/2, HTTP/3, gRPC.
    """

    def __init__(self):
        self._config: dict | None = None
        self._writer: TraceWriter | None = None
        self._process_resolver: ProcessResolver | None = None
        self._tls_passthrough: TLSPassthrough | None = None
        self._whitelist_patterns: list[str] = []
        self._blacklist_words: list[str] = []
        self._enabled: bool = False

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option("oximy_enabled", bool, False, "Enable AI traffic capture")
        loader.add_option("oximy_config", str, "", "Path to config.json")
        loader.add_option("oximy_output_dir", str, "~/.oximy/traces", "Output directory for traces")
        loader.add_option("oximy_verbose", bool, False, "Enable verbose logging")

    def configure(self, updated: set[str]) -> None:
        """Handle configuration changes."""
        if not ctx.options.oximy_enabled:
            if self._enabled:
                self._cleanup()
            self._enabled = False
            return

        self._enabled = True

        # Set up verbose logging
        if ctx.options.oximy_verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        # Load configuration files from addon directory
        addon_dir = Path(__file__).parent

        # Load whitelist
        whitelist_path = addon_dir / "whitelist.json"
        self._whitelist_patterns = load_whitelist(whitelist_path)

        # Load blacklist
        blacklist_path = addon_dir / "blacklist.json"
        self._blacklist_words = load_blacklist(blacklist_path)

        # Load passthrough patterns
        passthrough_path = addon_dir / "passthrough.json"
        passthrough_patterns = load_passthrough_patterns(passthrough_path)

        # Load output config
        config_path = Path(ctx.options.oximy_config) if ctx.options.oximy_config else addon_dir / "config.json"
        self._config = load_config(config_path if config_path.exists() else None)

        # Initialize writer
        output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        filename_pattern = self._config["output"].get("filename_pattern", "traces_{date}.jsonl")
        self._writer = TraceWriter(output_dir, filename_pattern)

        # Initialize process resolver
        self._process_resolver = ProcessResolver()

        # Initialize TLS passthrough for certificate-pinned hosts
        passthrough_cache = output_dir / "pinned_hosts.json"
        self._tls_passthrough = TLSPassthrough(passthrough_patterns, persist_path=passthrough_cache)

        # Enable system proxy
        _set_system_proxy(enable=True)

        logger.info("========== OXIMY ADDON STARTING ==========")
        logger.info(
            f"Whitelist: {len(self._whitelist_patterns)} domains, "
            f"Blacklist: {len(self._blacklist_words)} words"
        )
        logger.info(f"Output directory: {output_dir}")
        logger.info("========== OXIMY ADDON READY ==========")

    def _should_capture(self, host: str, path: str = "") -> bool:
        """Check if this request should be captured based on whitelist/blacklist."""
        # Check whitelist - returns matched pattern or None
        matched_pattern = matches_domain(host, self._whitelist_patterns)
        if not matched_pattern:
            logger.info(f"    SKIP (not in whitelist): {host}")
            return False

        logger.info(f"    MATCH: {host} -> pattern '{matched_pattern}'")

        # Check blacklist
        full_url = f"{host}{path}"
        if contains_blacklist_word(full_url, self._blacklist_words):
            logger.info(f"    BLOCKED (blacklist): {full_url}")
            return False

        return True

    # =========================================================================
    # HTTP Hooks
    # =========================================================================

    async def request(self, flow: http.HTTPFlow) -> None:
        """Capture client process info on request (before it exits)."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path

        logger.info(f">>> {flow.request.method} {host}{path[:80]}")

        if not self._should_capture(host, path):
            flow.metadata["oximy_skip"] = True
            return  # _should_capture already logged the skip/match reason

        # Mark for capture
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_start_time"] = time.time()
        logger.info(f"    CAPTURING: {host}{path[:80]}")

        # Capture client process info early (before process exits)
        if self._process_resolver:
            try:
                client_port = flow.client_conn.peername[1]
                client_process = await self._process_resolver.get_process_for_port(client_port)
                flow.metadata["oximy_client"] = client_process
            except Exception as e:
                logger.debug(f"Could not resolve client process: {e}")

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Handle response headers - ensure SSE streams wait for full body."""
        if not self._enabled or flow.metadata.get("oximy_skip"):
            return

        # For SSE and streaming responses, we want the full body
        # Don't set up streaming - let mitmproxy accumulate the full response
        pass

    def response(self, flow: http.HTTPFlow) -> None:
        """Capture full request/response and write to trace."""
        logger.info(f"<<< RESPONSE: {flow.request.pretty_host} status={flow.response.status_code if flow.response else 'None'}")

        if not self._enabled or not self._writer:
            logger.debug("Response skipped: not enabled or no writer")
            return

        if flow.metadata.get("oximy_skip"):
            logger.debug(f"Response skipped: oximy_skip set for {flow.request.pretty_host}")
            return

        if not flow.response:
            logger.debug("Response skipped: no response object")
            return

        # Check for WebSocket upgrade - these are handled by websocket_end
        if flow.websocket:
            return

        try:
            event = self._build_http_event(flow)
            if event:
                self._writer.write(event)
                logger.info(f"Captured HTTP: {flow.request.method} {flow.request.pretty_host}{flow.request.path[:50]}")
        except Exception as e:
            logger.error(f"Failed to capture HTTP: {e}")

    # =========================================================================
    # WebSocket Hooks
    # =========================================================================

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Accumulate WebSocket messages in flow metadata."""
        if not self._enabled:
            return

        host = flow.request.pretty_host
        path = flow.request.path

        if not self._should_capture(host, path):
            flow.metadata["oximy_skip"] = True
            return

        # Initialize message list if needed
        if "oximy_ws_messages" not in flow.metadata:
            flow.metadata["oximy_ws_messages"] = []
            flow.metadata["oximy_ws_start"] = time.time()

        # Get the latest message
        if flow.websocket and flow.websocket.messages:
            msg = flow.websocket.messages[-1]
            flow.metadata["oximy_ws_messages"].append({
                "direction": "client" if msg.from_client else "server",
                "timestamp": datetime.fromtimestamp(msg.timestamp, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "content": msg.content.decode("utf-8", errors="replace") if isinstance(msg.content, bytes) else str(msg.content),
            })

    def websocket_end(self, flow: http.HTTPFlow) -> None:
        """Write accumulated WebSocket messages as single trace on connection close."""
        if not self._enabled or not self._writer:
            return

        if flow.metadata.get("oximy_skip"):
            return

        messages = flow.metadata.get("oximy_ws_messages")
        if not messages:
            return

        try:
            event = self._build_websocket_event(flow)
            if event:
                self._writer.write(event)
                logger.info(f"Captured WebSocket: {flow.request.pretty_host}{flow.request.path[:30]} ({len(messages)} messages)")
        except Exception as e:
            logger.error(f"Failed to capture WebSocket: {e}")

    # =========================================================================
    # Event Building
    # =========================================================================

    def _build_http_event(self, flow: http.HTTPFlow) -> dict | None:
        """Build an HTTP trace event with raw request/response bodies."""
        event_id = generate_event_id()
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        # Calculate timing
        duration_ms = None
        ttfb_ms = None
        if flow.request.timestamp_start and flow.response:
            if flow.response.timestamp_end:
                duration_ms = int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000)
            if flow.response.timestamp_start:
                ttfb_ms = int((flow.response.timestamp_start - flow.request.timestamp_start) * 1000)

        # Get client process info
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")

        # Get raw request body
        request_body = None
        if flow.request.content:
            try:
                request_body = flow.request.content.decode("utf-8")
            except UnicodeDecodeError:
                request_body = flow.request.content.hex()

        # Get raw response body
        response_body = None
        if flow.response and flow.response.content:
            try:
                response_body = flow.response.content.decode("utf-8")
            except UnicodeDecodeError:
                response_body = flow.response.content.hex()

        event = {
            "event_id": event_id,
            "timestamp": timestamp,
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
                "body": response_body,
            },
            "timing": {
                "duration_ms": duration_ms,
                "ttfb_ms": ttfb_ms,
            },
        }

        if client_process:
            event["client"] = client_process.to_dict()

        return event

    def _build_websocket_event(self, flow: http.HTTPFlow) -> dict | None:
        """Build a WebSocket trace event with all accumulated messages."""
        event_id = generate_event_id()
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        messages = flow.metadata.get("oximy_ws_messages", [])
        start_time = flow.metadata.get("oximy_ws_start", time.time())
        duration_ms = int((time.time() - start_time) * 1000)

        # Get client process info (from HTTP upgrade request)
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")

        event = {
            "event_id": event_id,
            "timestamp": timestamp,
            "type": "websocket",
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "messages": messages,
            "timing": {
                "duration_ms": duration_ms,
                "message_count": len(messages),
            },
        }

        if client_process:
            event["client"] = client_process.to_dict()

        return event

    # =========================================================================
    # TLS Hooks - Handle certificate pinning passthrough
    # =========================================================================

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """Check if host should bypass TLS interception."""
        if self._enabled and self._tls_passthrough:
            self._tls_passthrough.tls_clienthello(data)

    def tls_failed_client(self, data: tls.TlsData) -> None:
        """Record TLS failures to learn certificate-pinned hosts."""
        if self._enabled and self._tls_passthrough:
            self._tls_passthrough.tls_failed_client(data)

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def done(self) -> None:
        """Cleanup on shutdown."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        # Disable system proxy
        _set_system_proxy(enable=False)

        if self._writer:
            self._writer.close()
            self._writer = None
        if self._process_resolver:
            self._process_resolver.clear_cache()
            self._process_resolver = None
        self._tls_passthrough = None
        self._enabled = False
        logger.info("Oximy addon disabled")


# Register addon
addons = [OximyAddon()]
