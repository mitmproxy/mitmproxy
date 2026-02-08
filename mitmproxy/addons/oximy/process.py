"""Process attribution for Oximy addon."""

from __future__ import annotations

import asyncio
import ctypes
import ctypes.util
import logging
import platform
from dataclasses import dataclass

# psutil is optional - provides faster process resolution (~2-5ms vs 50-500ms with lsof)
# Falls back to subprocess-based methods if not available
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore
    _HAS_PSUTIL = False

logger = logging.getLogger(__name__)

# --- macOS Responsible Process API ---
# Uses the private API responsibility_get_pid_responsible_for_pid() to trace
# XPC services (e.g., com.apple.WebKit.Networking) back to the originating app.
# This is the same mechanism Activity Monitor uses for process trees.
_responsible_pid_func = None
_proc_pidpath_func = None

if platform.system() == "Darwin":
    try:
        _libSystem = ctypes.CDLL(ctypes.util.find_library("System") or "/usr/lib/libSystem.B.dylib")
        _responsible_pid_func = _libSystem.responsibility_get_pid_responsible_for_pid
        _responsible_pid_func.argtypes = [ctypes.c_int]
        _responsible_pid_func.restype = ctypes.c_int
    except (OSError, AttributeError):
        pass  # API not available on this macOS version

    try:
        _libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
        _proc_pidpath_func = _libproc.proc_pidpath
        _proc_pidpath_func.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        _proc_pidpath_func.restype = ctypes.c_int
    except (OSError, AttributeError):
        pass


def _get_responsible_pid(pid: int) -> int | None:
    """Get the macOS 'responsible' PID for a process.

    Uses the private API responsibility_get_pid_responsible_for_pid()
    to trace XPC services back to their originating apps.
    Returns the responsible PID, or None if unavailable or same as input.
    """
    if not _responsible_pid_func:
        return None
    try:
        result = _responsible_pid_func(pid)
        if result > 0 and result != pid:
            return result
    except (OSError, ValueError):
        pass
    return None


def _proc_pidpath(pid: int) -> str | None:
    """Get process executable path using libproc (faster than ps subprocess)."""
    if not _proc_pidpath_func:
        return None
    try:
        buf = ctypes.create_string_buffer(4096)
        ret = _proc_pidpath_func(pid, buf, 4096)
        if ret > 0:
            return buf.value.decode("utf-8")
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    return None


# Known macOS system services that delegate networking on behalf of other apps
_MACOS_SYSTEM_SERVICES = frozenset({
    "com.apple.webkit.networking",
    "com.apple.webkit.webcontent",
    "com.apple.webkit.gpu",
    "com.apple.nsurlsessiond",
    "com.apple.cfnetwork",
    "com.apple.networkserviceproxy",
})


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


class ProcessResolver:
    """Resolves network connections to originating processes.

    Uses platform-specific tools to map network ports to process information:
    - macOS/Linux: lsof for port lookup, ps for process info
    - Windows: netstat for port lookup, wmic for process info

    The resolver queries the proxy port (always active) rather than ephemeral
    client ports to avoid timing issues where connections close before lookup.
    """

    def __init__(self, proxy_port: int = 0):
        """Initialize the ProcessResolver.

        Args:
            proxy_port: The proxy's listening port. Used to query active
                        connections and filter for specific client ports.
                        Call update_proxy_port() once the actual port is known.
        """
        self._proxy_port = proxy_port
        self._cache: dict[int, dict] = {}  # PID -> process info
        self._bundle_id_cache: dict[str, str | None] = {}  # app_path -> bundle_id
        self._port_cache: dict[int, tuple[ClientProcess, float]] = {}  # port -> (ClientProcess, timestamp)
        self._port_cache_ttl = 60.0  # Cache port->process mapping for 60 seconds (fail-open: longer TTL reduces blocking lookups)
        self._resolution_timeout = 0.5  # Fail-open: max time to wait for process resolution before returning None

        self._is_macos = platform.system() == "Darwin"
        self._is_linux = platform.system() == "Linux"
        self._is_windows = platform.system() == "Windows"
        self._bundle_cache_prepopulated = False
        self._bundle_cache_task: asyncio.Task | None = None

    def update_proxy_port(self, port: int) -> None:
        """Update the proxy port after the actual listening port is known."""
        self._proxy_port = port

    async def get_process_for_port(self, port: int) -> ClientProcess:
        """Get process information for a connection on the given local port.

        FAIL-OPEN: This method is designed to never block requests for long.
        If resolution takes longer than _resolution_timeout (500ms), it returns
        a placeholder result immediately. The proxy continues working even if
        process attribution fails.
        """
        import time

        # Lazily trigger bundle cache prepopulation (non-blocking background task)
        if self._is_macos and not self._bundle_cache_prepopulated:
            self._bundle_cache_prepopulated = True
            self._bundle_cache_task = asyncio.create_task(self._prepopulate_bundle_cache())

        # Check port cache first (avoids expensive lsof/netstat calls)
        if port in self._port_cache:
            cached_process, timestamp = self._port_cache[port]
            if time.time() - timestamp < self._port_cache_ttl:
                return cached_process
            # Cache expired, remove it
            del self._port_cache[port]

        # FAIL-OPEN: Wrap the actual resolution in a timeout
        # If it takes too long, return immediately with unknown process
        try:
            return await asyncio.wait_for(
                self._get_process_for_port_impl(port),
                timeout=self._resolution_timeout
            )
        except asyncio.TimeoutError:
            logger.debug(f"[PROCESS] Resolution timeout for port {port} - proceeding without attribution (fail-open)")
            return ClientProcess(
                pid=None,
                name="Unknown (timeout)",
                path=None,
                ppid=None,
                parent_name=None,
                user=None,
                port=port,
                bundle_id=None,
            )

    async def _get_process_for_port_impl(self, port: int) -> ClientProcess:
        """Internal implementation of process resolution."""
        import time

        if not (self._is_macos or self._is_linux or self._is_windows):
            return ClientProcess(
                pid=None,
                name="Unknown (unsupported platform)",
                path=None,
                ppid=None,
                parent_name=None,
                user=None,
                port=port,
                bundle_id=None,
            )

        # Step 1: Find PID that owns this port
        pid = await self._find_pid_for_port(port)
        if pid is None:
            logger.debug(f"[PROCESS] Could not find PID for port {port} - process may have exited")
            return ClientProcess(
                pid=None,
                name="Unknown (exited)",
                path=None,
                ppid=None,
                parent_name=None,
                user=None,
                port=port,
                bundle_id=None,
            )

        # Step 2: Get process info (with caching)
        proc_info = await self._get_process_info(pid)
        if proc_info is None:
            return ClientProcess(
                pid=pid,
                name="Unknown (exited)",
                path=None,
                ppid=None,
                parent_name=None,
                user=None,
                port=port,
                bundle_id=None,
            )

        # Step 3: Get parent info if parent is meaningful (not launchd/init)
        parent_name = None
        if proc_info.get("ppid") and proc_info["ppid"] > 1:
            parent_info = await self._get_process_info(proc_info["ppid"])
            if parent_info:
                parent_name = self._extract_name(parent_info.get("path"))

        name = self._extract_name(proc_info.get("path"))
        bundle_id = await self._extract_bundle_id(proc_info.get("path"))

        # Step 4 (macOS only): Resolve responsible process
        # Always try responsible PID on macOS — any process might delegate networking
        # via XPC services, helper processes, or system daemons.
        # The ctypes call is <0.1ms so there's no performance concern.
        resp_proc_info = None  # Track responsible process info for ClientProcess fields
        if self._is_macos:
            # Classify for logging only
            if bundle_id and bundle_id.lower() in _MACOS_SYSTEM_SERVICES:
                resolved_via = "system_service"
            elif not bundle_id:
                resolved_via = "no_bundle_id"
            else:
                resolved_via = "app_delegation_check"

            responsible_pid = _get_responsible_pid(pid)
            if responsible_pid:
                resp_path = _proc_pidpath(responsible_pid)
                if resp_path:
                    resp_bundle_id = await self._extract_bundle_id(resp_path)
                    if resp_bundle_id and resp_bundle_id != bundle_id:
                        logger.info(
                            f"[PROCESS] Responsible PID: {bundle_id or name} (PID {pid}) "
                            f"-> {resp_bundle_id} (PID {responsible_pid}) [{resolved_via}]"
                        )
                        bundle_id = resp_bundle_id
                        name = self._extract_name(resp_path)
                        pid = responsible_pid
                        # Get full process info for the responsible process
                        resp_proc_info = await self._get_process_info(responsible_pid)
                else:
                    # libproc failed, fall back to ps for both path and info
                    resp_proc_info = await self._get_process_info(responsible_pid)
                    if resp_proc_info:
                        resp_bundle_id = await self._extract_bundle_id(resp_proc_info.get("path"))
                        if resp_bundle_id and resp_bundle_id != bundle_id:
                            logger.info(
                                f"[PROCESS] Responsible PID (ps): {bundle_id or name} (PID {pid}) "
                                f"-> {resp_bundle_id} (PID {responsible_pid}) [{resolved_via}]"
                            )
                            bundle_id = resp_bundle_id
                            name = self._extract_name(resp_proc_info.get("path"))
                            pid = responsible_pid

        # Step 5 (macOS): Walk parent process tree if still no bundle_id.
        # This resolves CLI processes (node, python, curl) spawned inside a
        # terminal app by tracing: node → zsh → Terminal.app / Cursor.app.
        if not bundle_id and self._is_macos:
            ancestor_pid = proc_info.get("ppid")
            depth = 0
            while ancestor_pid and ancestor_pid > 1 and depth < 10:
                ancestor_info = await self._get_process_info(ancestor_pid)
                if not ancestor_info:
                    break
                ancestor_bundle = await self._extract_bundle_id(ancestor_info.get("path"))
                if ancestor_bundle:
                    logger.info(
                        f"[PROCESS] Parent walk: {name} (PID {pid}) "
                        f"-> {ancestor_bundle} (PID {ancestor_pid}, depth={depth + 1})"
                    )
                    bundle_id = ancestor_bundle
                    break
                ancestor_pid = ancestor_info.get("ppid")
                depth += 1

        # On Windows, use exe name as bundle_id fallback
        if not bundle_id and self._is_windows:
            bundle_id = self._extract_exe_name(proc_info.get("path"))

        # Use responsible process info if we resolved through it, otherwise original
        final_info = resp_proc_info if resp_proc_info else proc_info

        result = ClientProcess(
            pid=pid,
            name=name,
            path=final_info.get("path"),
            ppid=final_info.get("ppid"),
            parent_name=parent_name,
            user=final_info.get("user"),
            port=port,
            bundle_id=bundle_id,
        )

        # Cache the result to avoid expensive subprocess calls for same port
        self._port_cache[port] = (result, time.time())

        # Limit cache size to prevent memory growth
        if len(self._port_cache) > 1000:
            # Remove oldest entries
            sorted_entries = sorted(self._port_cache.items(), key=lambda x: x[1][1])
            for old_port, _ in sorted_entries[:500]:
                del self._port_cache[old_port]

        return result

    async def _find_pid_for_port(self, port: int) -> int | None:
        """Find PID that owns a local port. Cross-platform using psutil.

        On macOS, psutil.net_connections() requires root, so we iterate
        user-owned processes and check their connections individually (~18ms).
        """
        if not _HAS_PSUTIL:
            return None

        try:
            loop = asyncio.get_event_loop()
            pid = await loop.run_in_executor(
                None, lambda: self._find_pid_for_port_sync(port)
            )
            return pid
        except Exception as e:
            logger.debug(f"[PSUTIL] Lookup failed for port {port}: {e}")

        return None

    def _find_pid_for_port_sync(self, port: int) -> int | None:
        """Synchronous PID lookup by iterating user-owned processes.

        This avoids psutil.net_connections() which requires root on macOS.
        Instead, iterates each process's connections (~18ms total).
        """
        import os
        uid = os.getuid() if hasattr(os, "getuid") else None
        fallback_pid: int | None = None

        for proc in psutil.process_iter(["pid", "uids"]):
            try:
                # On Unix, skip processes owned by other users
                if uid is not None:
                    proc_uids = proc.info.get("uids")
                    if proc_uids and proc_uids.real != uid:
                        continue

                for conn in proc.net_connections(kind="tcp"):
                    if not conn.laddr or conn.laddr.port != port:
                        continue
                    # Primary: match client port connecting TO our proxy
                    if conn.raddr and conn.raddr.port == self._proxy_port:
                        logger.debug(f"[PSUTIL] Found PID {proc.pid} for port {port}")
                        return proc.pid
                    # Fallback: match just by local port (no raddr or different dest)
                    if fallback_pid is None:
                        fallback_pid = proc.pid

            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue

        if fallback_pid is not None:
            logger.debug(f"[PSUTIL] Found PID {fallback_pid} for port {port} (fallback)")
        return fallback_pid

    async def _get_process_info(self, pid: int) -> dict | None:
        """Get process information for a PID, using cache if available."""
        if pid in self._cache:
            return self._cache[pid]

        info = await self._fetch_process_info(pid)
        if info:
            self._cache[pid] = info

        return info

    async def _fetch_process_info(self, pid: int) -> dict | None:
        """Fetch process info using psutil. Cross-platform."""
        if _HAS_PSUTIL:
            try:
                proc = psutil.Process(pid)
                return {
                    "pid": pid,
                    "ppid": proc.ppid(),
                    "user": proc.username(),
                    "path": proc.exe(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.debug(f"[PSUTIL] Failed for PID {pid}: {e}")

        # macOS fallback: use libproc for path
        if self._is_macos:
            path = _proc_pidpath(pid)
            if path:
                return {"pid": pid, "ppid": None, "user": None, "path": path}

        return None

    def _extract_name(self, path: str | None) -> str | None:
        """Extract process name from path."""
        if not path:
            return None
        if "\\" in path:
            name = path.rsplit("\\", 1)[-1]
        else:
            name = path.rsplit("/", 1)[-1]
        if name.lower().endswith(".exe"):
            name = name[:-4]
        return name if name else None

    def _extract_exe_name(self, path: str | None) -> str | None:
        """Extract exe filename from Windows path (e.g. 'chrome.exe')."""
        if not path:
            return None
        if "\\" in path:
            exe = path.rsplit("\\", 1)[-1]
        else:
            exe = path.rsplit("/", 1)[-1]
        return exe if exe and exe.lower().endswith(".exe") else None

    async def _extract_bundle_id(self, path: str | None) -> str | None:
        """Extract macOS bundle identifier from an app path or process name.

        Handles:
        - .app bundles (e.g., /Applications/Safari.app/Contents/MacOS/Safari)
        - .xpc services (e.g., com.apple.WebKit.Networking.xpc)
        - Process names that are already bundle IDs (e.g., com.apple.WebKit.Networking)
        """
        if not path or not self._is_macos:
            return None

        # Check cache first
        if path in self._bundle_id_cache:
            return self._bundle_id_cache[path]

        bundle_id = None

        # Strategy 1: Extract from .app bundle
        if ".app" in path:
            bundle_id = await self._extract_bundle_id_from_app(path)

        # Strategy 2: Extract from .xpc bundle
        if not bundle_id and ".xpc" in path:
            bundle_id = await self._extract_bundle_id_from_xpc(path)

        # Strategy 3: Check if process name itself is a bundle ID
        # (reverse domain format: com.company.product or similar)
        if not bundle_id:
            name = self._extract_name(path)
            if name and self._looks_like_bundle_id(name):
                bundle_id = name

        self._bundle_id_cache[path] = bundle_id
        return bundle_id

    def _looks_like_bundle_id(self, name: str) -> bool:
        """Check if a string looks like a reverse-domain bundle identifier."""
        # Bundle IDs typically have format: com.company.product or similar
        # Must have at least 2 dots and start with known prefixes
        if not name or name.count('.') < 2:
            return False
        parts = name.split('.')
        # Common prefixes for bundle IDs
        known_prefixes = ('com', 'org', 'net', 'io', 'app', 'me', 'co', 'dev')
        return parts[0].lower() in known_prefixes and all(p.replace('-', '').replace('_', '').isalnum() for p in parts)

    async def _extract_bundle_id_from_app(self, path: str) -> str | None:
        """Extract bundle ID from a .app bundle's Info.plist."""
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
            logger.debug(f"Failed to extract bundle_id from app {path}: {e}")
        return None

    async def _extract_bundle_id_from_xpc(self, path: str) -> str | None:
        """Extract bundle ID from a .xpc service's Info.plist."""
        try:
            xpc_path = path.split(".xpc")[0] + ".xpc"
            if xpc_path in self._bundle_id_cache:
                return self._bundle_id_cache[xpc_path]

            plist_path = f"{xpc_path}/Contents/Info.plist"
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
                self._bundle_id_cache[xpc_path] = None
                return None

            if proc.returncode == 0 and stdout.strip():
                bundle_id = stdout.decode().strip()
                self._bundle_id_cache[xpc_path] = bundle_id
                return bundle_id

            self._bundle_id_cache[xpc_path] = None
        except OSError as e:
            logger.debug(f"Failed to extract bundle_id from xpc {path}: {e}")
        return None

    async def _prepopulate_bundle_cache(self) -> None:
        """Pre-populate bundle ID cache by scanning /Applications.

        FAIL-OPEN: This runs in the background and doesn't block startup.
        If it fails or takes too long, the resolver continues working
        with on-demand lookups.
        """
        import os

        try:
            apps_dir = "/Applications"
            if not os.path.isdir(apps_dir):
                return

            # Scan only top-level .app bundles to avoid slow deep scans
            app_count = 0
            for entry in os.listdir(apps_dir):
                if not entry.endswith(".app"):
                    continue

                app_path = os.path.join(apps_dir, entry)
                plist_path = os.path.join(app_path, "Contents", "Info.plist")

                if not os.path.exists(plist_path):
                    continue

                try:
                    proc = await asyncio.create_subprocess_exec(
                        "defaults", "read", plist_path, "CFBundleIdentifier",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    try:
                        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=0.5)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                        continue

                    if proc.returncode == 0 and stdout.strip():
                        bundle_id = stdout.decode().strip()
                        self._bundle_id_cache[app_path] = bundle_id
                        app_count += 1

                except OSError:
                    continue

                # Yield to other tasks periodically
                if app_count % 10 == 0:
                    await asyncio.sleep(0)

            logger.info(f"[PROCESS] Pre-populated bundle cache with {app_count} applications")

        except Exception as e:
            # FAIL-OPEN: Don't crash if prepopulation fails
            logger.debug(f"[PROCESS] Bundle cache prepopulation failed (non-fatal): {e}")

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._bundle_id_cache.clear()
        self._port_cache.clear()
