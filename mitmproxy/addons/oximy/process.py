"""
Process attribution for Oximy addon.

Maps network connections back to originating processes by querying
the kernel for socket ownership information.
"""

from __future__ import annotations

import logging
import platform
import subprocess
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
        self._is_macos = platform.system() == "Darwin"
        self._is_linux = platform.system() == "Linux"
        self._bundle_id_to_app_id: dict[str, str] = {}  # bundle_id -> app_id

    def set_bundle_id_index(self, index: dict[str, str]) -> None:
        """Set the bundle_id -> app_id mapping from the registry."""
        self._bundle_id_to_app_id = index

    def get_process_for_port(self, port: int) -> ClientProcess:
        """
        Get process information for a connection on the given local port.

        Args:
            port: The client's ephemeral source port

        Returns:
            ClientProcess with available information, or minimal info on failure
        """
        if not (self._is_macos or self._is_linux):
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
        pid = self._find_pid_for_port(port)
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
        proc_info = self._get_process_info(pid)
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
            parent_info = self._get_process_info(proc_info["ppid"])
            if parent_info:
                parent_name = self._extract_name(parent_info.get("path"))

        # Step 4: Decide which name to surface
        # If parent exists and is meaningful, prefer parent context
        # The actual process name is still available in the full info
        name = self._extract_name(proc_info.get("path"))

        # Step 5: Extract bundle_id from path (macOS apps)
        bundle_id = self._extract_bundle_id(proc_info.get("path"))

        # Step 6: Look up app_id from bundle_id
        app_id = self._bundle_id_to_app_id.get(bundle_id) if bundle_id else None

        return ClientProcess(
            pid=pid,
            name=name,
            path=proc_info.get("path"),
            ppid=proc_info.get("ppid"),
            parent_name=parent_name,
            user=proc_info.get("user"),
            port=port,
            bundle_id=bundle_id,
            id=app_id,
        )

    def _find_pid_for_port(self, port: int) -> int | None:
        """
        Find the PID that owns a local port as the SOURCE (client side).

        When looking up port 54029, lsof returns both sides:
        - Python ... 127.0.0.1:8088->127.0.0.1:54029 (proxy, port is DEST)
        - Comet  ... 127.0.0.1:54029->127.0.0.1:8088 (client, port is SOURCE)

        We want the client side where the port is the source.
        """
        try:
            # Use regular lsof output (not -F) so we can parse the connection direction
            result = subprocess.run(
                ["lsof", "-i", f"TCP:{port}", "-n", "-P"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[1:]:  # Skip header
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

        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            logger.debug(f"Failed to find PID for port {port}: {e}")

        return None

    def _get_process_info(self, pid: int) -> dict | None:
        """
        Get process information for a PID, using cache if available.

        Returns dict with keys: pid, ppid, user, path
        """
        if pid in self._cache:
            return self._cache[pid]

        info = self._fetch_process_info(pid)
        if info:
            self._cache[pid] = info

        return info

    def _fetch_process_info(self, pid: int) -> dict | None:
        """Fetch process info from the system using ps."""
        try:
            # Single ps call to get all needed info
            # Format: pid, ppid, user, full command path
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "pid=,ppid=,user=,comm="],
                capture_output=True,
                text=True,
                timeout=1,
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(None, 3)
                if len(parts) >= 4:
                    return {
                        "pid": int(parts[0]),
                        "ppid": int(parts[1]),
                        "user": parts[2],
                        "path": parts[3],
                    }
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            logger.debug(f"Failed to get process info for PID {pid}: {e}")

        return None

    def _extract_name(self, path: str | None) -> str | None:
        """Extract a readable process name from a path."""
        if not path:
            return None

        # Get the last component of the path
        name = path.rsplit("/", 1)[-1]

        # Clean up macOS app bundle names
        # e.g., "Cursor Helper (Renderer)" stays as is
        # e.g., "/Applications/Cursor.app/Contents/MacOS/Cursor" -> "Cursor"

        return name if name else None

    def _extract_bundle_id(self, path: str | None) -> str | None:
        """Extract macOS bundle identifier from an app path."""
        if not path or not self._is_macos:
            return None

        # Find the .app bundle in the path
        # e.g., "/Applications/Arc.app/Contents/..." -> "/Applications/Arc.app"
        if ".app" not in path:
            return None

        try:
            app_path = path.split(".app")[0] + ".app"
            plist_path = f"{app_path}/Contents/Info.plist"

            # Use defaults to read bundle identifier from plist
            result = subprocess.run(
                ["defaults", "read", plist_path, "CFBundleIdentifier"],
                capture_output=True,
                text=True,
                timeout=1,
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Failed to extract bundle_id from {path}: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear the process info cache."""
        self._cache.clear()
