"""
Process attribution for Oximy addon.

Maps network connections back to originating processes by querying
the kernel for socket ownership information.
"""

from __future__ import annotations

import asyncio
import logging
import platform
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClientProcess:
    """Information about the client process that made a request."""

    pid: int | None
    name: str | None  # e.g., "curl", "python3.11"
    path: str | None  # e.g., "/usr/bin/curl"
    ppid: int | None  # Parent PID
    parent_name: str | None  # e.g., "Cursor" for "Cursor Helper"
    user: str | None
    port: int  # The ephemeral port used for lookup
    bundle_id: str | None = None  # macOS bundle identifier
    id: str | None = None  # App ID from registry (e.g., "granola")

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
        if self.id is not None:
            result["id"] = self.id

        return result


class ProcessResolver:
    """
    Resolves network connections to originating processes.

    Uses a cache to avoid repeated lookups for the same PID.
    Strategy: Look up parent process first (more useful for helper processes),
    fall back to actual process if parent is launchd/init.
    """

    def __init__(self):
        self._cache: dict[int, dict] = {}  # PID -> process info
        self._bundle_id_cache: dict[str, str | None] = {}  # app_path -> bundle_id
        self._is_macos = platform.system() == "Darwin"
        self._is_linux = platform.system() == "Linux"
        self._is_windows = platform.system() == "Windows"
        self._bundle_id_to_app_id: dict[str, str] = {}  # bundle_id -> app_id

    def set_bundle_id_index(self, index: dict[str, str]) -> None:
        """Set the bundle_id/exe -> app_id mapping from the registry.

        On macOS, this maps bundle_id -> app_id.
        On Windows, this maps exe name -> app_id.
        """
        self._bundle_id_to_app_id = index

    async def get_process_for_port(self, port: int) -> ClientProcess:
        """
        Get process information for a connection on the given local port.

        Args:
            port: The client's ephemeral source port

        Returns:
            ClientProcess with available information, or minimal info on failure
        """
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

        # Step 4: Decide which name to surface
        # If parent exists and is meaningful, prefer parent context
        # The actual process name is still available in the full info
        name = self._extract_name(proc_info.get("path"))

        # Step 5: Extract bundle_id from path (macOS apps) or exe name (Windows)
        bundle_id = await self._extract_bundle_id(proc_info.get("path"))

        # Step 6: Look up app_id from bundle_id (macOS) or exe name (Windows)
        app_id = None
        exe_name = None
        if bundle_id:
            # macOS: use bundle_id
            app_id = self._bundle_id_to_app_id.get(bundle_id)
        elif self._is_windows:
            # Windows: extract exe name and use it for lookup
            exe_name = self._extract_exe_name(proc_info.get("path"))
            if exe_name:
                # Try exact match first, then lowercase
                app_id = self._bundle_id_to_app_id.get(exe_name)
                if not app_id:
                    app_id = self._bundle_id_to_app_id.get(exe_name.lower())
            # Also try parent exe name for helper processes
            if not app_id and parent_name:
                parent_exe = f"{parent_name}.exe"
                app_id = self._bundle_id_to_app_id.get(parent_exe)
                if not app_id:
                    app_id = self._bundle_id_to_app_id.get(parent_exe.lower())

        return ClientProcess(
            pid=pid,
            name=name,
            path=proc_info.get("path"),
            ppid=proc_info.get("ppid"),
            parent_name=parent_name,
            user=proc_info.get("user"),
            port=port,
            bundle_id=bundle_id if bundle_id else exe_name,  # Use exe_name as identifier on Windows
            id=app_id,
        )

    async def _find_pid_for_port(self, port: int) -> int | None:
        """
        Find the PID that owns a local port as the SOURCE (client side).

        When looking up port 54029, lsof returns both sides:
        - Python ... 127.0.0.1:8088->127.0.0.1:54029 (proxy, port is DEST)
        - Comet  ... 127.0.0.1:54029->127.0.0.1:8088 (client, port is SOURCE)

        We want the client side where the port is the source.
        """
        if self._is_windows:
            return await self._find_pid_for_port_windows(port)

        try:
            # Use regular lsof output (not -F) so we can parse the connection direction
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
                logger.debug(f"lsof timed out for port {port}")
                return None

            if proc.returncode == 0:
                for line in stdout.decode().strip().split("\n")[1:]:  # Skip header
                    # Look for lines where our port is the SOURCE (left side of ->)
                    # Format: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME (STATE)
                    # NAME is like: 127.0.0.1:54029->127.0.0.1:8088
                    # STATE is like: (ESTABLISHED) or (CLOSE_WAIT)
                    parts = line.split()
                    if len(parts) >= 9:
                        # Connection string can be last or second-to-last
                        # (depends on whether state is shown)
                        for field in [parts[-1], parts[-2]]:
                            if f":{port}->" in field:
                                return int(parts[1])  # PID is second field

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to find PID for port {port}: {e}")

        return None

    async def _find_pid_for_port_windows(self, port: int) -> int | None:
        """
        Find the PID that owns a local port on Windows using netstat.

        Uses 'netstat -aon' which shows:
        Proto  Local Address          Foreign Address        State           PID
        TCP    127.0.0.1:54029        127.0.0.1:8088         ESTABLISHED     1234
        """
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
                logger.debug(f"netstat timed out for port {port}")
                return None

            if proc.returncode == 0:
                for line in stdout.decode().strip().split("\n"):
                    # Skip header lines
                    if not line.strip() or "Proto" in line:
                        continue

                    parts = line.split()
                    if len(parts) >= 5 and parts[0] == "TCP":
                        # Local Address is parts[1], e.g., "127.0.0.1:54029"
                        local_addr = parts[1]
                        # Check if our port is the local (source) port
                        if local_addr.endswith(f":{port}"):
                            try:
                                return int(parts[4])  # PID is last field
                            except ValueError:
                                continue

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to find PID for port {port} on Windows: {e}")

        return None

    async def _get_process_info(self, pid: int) -> dict | None:
        """
        Get process information for a PID, using cache if available.

        Returns dict with keys: pid, ppid, user, path
        """
        if pid in self._cache:
            return self._cache[pid]

        info = await self._fetch_process_info(pid)
        if info:
            self._cache[pid] = info

        return info

    async def _fetch_process_info(self, pid: int) -> dict | None:
        """Fetch process info from the system using ps (Unix) or wmic (Windows)."""
        if self._is_windows:
            return await self._fetch_process_info_windows(pid)

        try:
            # Single ps call to get all needed info
            # Format: pid, ppid, user, full command path
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
                logger.debug(f"ps timed out for PID {pid}")
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
            # Use wmic to get process info
            # wmic process where processid=1234 get name,executablepath,parentprocessid /format:csv
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
                logger.debug(f"wmic timed out for PID {pid}")
                return None

            if proc.returncode == 0 and stdout.strip():
                # CSV format: Node,ExecutablePath,Name,ParentProcessId
                lines = stdout.decode().strip().split("\n")
                for line in lines:
                    if not line.strip() or line.startswith("Node"):
                        continue
                    parts = line.strip().split(",")
                    if len(parts) >= 4:
                        # parts: [Node, ExecutablePath, Name, ParentProcessId]
                        exe_path = parts[1] if parts[1] else None
                        name = parts[2] if parts[2] else None
                        try:
                            ppid = int(parts[3]) if parts[3] else None
                        except ValueError:
                            ppid = None

                        # Get user for this process
                        user = await self._get_process_user_windows(pid)

                        return {
                            "pid": pid,
                            "ppid": ppid,
                            "user": user,
                            "path": exe_path or name,
                        }

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to get process info for PID {pid} on Windows: {e}")

        return None

    async def _get_process_user_windows(self, pid: int) -> str | None:
        """Get the username that owns a process on Windows."""
        try:
            # Use tasklist with verbose mode to get user info
            # tasklist /FI "PID eq 1234" /FO CSV /V
            proc = await asyncio.create_subprocess_exec(
                "tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/V",
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
                if len(lines) >= 2:
                    # Parse CSV: "Image Name","PID","Session Name","Session#","Mem Usage","Status","User Name","CPU Time","Window Title"
                    # User Name is the 7th field (index 6)
                    data_line = lines[1]
                    # Simple CSV parsing (fields are quoted)
                    parts = []
                    current = ""
                    in_quotes = False
                    for char in data_line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == ',' and not in_quotes:
                            parts.append(current.strip('"'))
                            current = ""
                        else:
                            current += char
                    parts.append(current.strip('"'))

                    if len(parts) >= 7:
                        user = parts[6]
                        # User might be "DOMAIN\username" or "N/A"
                        if user and user != "N/A":
                            # Strip domain prefix if present
                            if "\\" in user:
                                user = user.split("\\")[-1]
                            return user

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to get user for PID {pid} on Windows: {e}")

        return None

    def _extract_name(self, path: str | None) -> str | None:
        """Extract a readable process name from a path."""
        if not path:
            return None

        # Get the last component of the path (handle both Unix and Windows)
        # Try backslash first (Windows), then forward slash (Unix)
        if "\\" in path:
            name = path.rsplit("\\", 1)[-1]
        else:
            name = path.rsplit("/", 1)[-1]

        # Remove .exe extension on Windows for cleaner display
        if name.lower().endswith(".exe"):
            name = name[:-4]

        # Clean up macOS app bundle names
        # e.g., "Cursor Helper (Renderer)" stays as is
        # e.g., "/Applications/Cursor.app/Contents/MacOS/Cursor" -> "Cursor"

        return name if name else None

    def _extract_exe_name(self, path: str | None) -> str | None:
        """Extract the executable filename from a Windows path.

        Returns the full exe name including .exe extension for registry matching.
        e.g., "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" -> "chrome.exe"
        """
        if not path:
            return None

        # Get the last component of the path
        if "\\" in path:
            exe = path.rsplit("\\", 1)[-1]
        else:
            exe = path.rsplit("/", 1)[-1]

        # Only return if it looks like an exe
        if exe and exe.lower().endswith(".exe"):
            return exe

        return None

    async def _extract_bundle_id(self, path: str | None) -> str | None:
        """Extract macOS bundle identifier from an app path."""
        if not path or not self._is_macos:
            return None

        # Find the .app bundle in the path
        # e.g., "/Applications/Arc.app/Contents/..." -> "/Applications/Arc.app"
        if ".app" not in path:
            return None

        try:
            app_path = path.split(".app")[0] + ".app"

            # Check cache first
            if app_path in self._bundle_id_cache:
                return self._bundle_id_cache[app_path]

            plist_path = f"{app_path}/Contents/Info.plist"

            # Use defaults to read bundle identifier from plist
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
                self._bundle_id_cache[app_path] = None  # Cache negative result
                return None

            if proc.returncode == 0 and stdout.strip():
                bundle_id = stdout.decode().strip()
                self._bundle_id_cache[app_path] = bundle_id  # Cache result
                return bundle_id

            # Cache negative result
            self._bundle_id_cache[app_path] = None

        except OSError as e:
            logger.debug(f"Failed to extract bundle_id from {path}: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear the process info cache."""
        self._cache.clear()
        self._bundle_id_cache.clear()
