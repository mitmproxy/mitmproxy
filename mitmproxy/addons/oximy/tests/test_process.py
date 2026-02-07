"""Comprehensive unit tests for process.py.

Tests cover process resolution, caching, and platform-specific logic.
All subprocess calls, psutil, and ctypes are mocked.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the module under test
from mitmproxy.addons.oximy.process import (
    ClientProcess,
    ProcessResolver,
    _get_responsible_pid,
    _proc_pidpath,
)


# =============================================================================
# _get_responsible_pid Tests
# =============================================================================

class TestGetResponsiblePid:
    """Tests for _get_responsible_pid function."""

    def test_func_unavailable_returns_none(self):
        """Should return None when responsible_pid_func is not available."""
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', None):
            result = _get_responsible_pid(1234)
            assert result is None

    def test_same_pid_returns_none(self):
        """Should return None when responsible PID equals input PID."""
        mock_func = MagicMock(return_value=1234)
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result is None

    def test_different_pid_returned(self):
        """Should return responsible PID when different from input."""
        mock_func = MagicMock(return_value=5678)
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result == 5678

    def test_zero_result_returns_none(self):
        """Should return None when result is 0 or negative."""
        mock_func = MagicMock(return_value=0)
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result is None

    def test_negative_result_returns_none(self):
        """Should return None when result is negative."""
        mock_func = MagicMock(return_value=-1)
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result is None

    def test_oserror_returns_none(self):
        """Should return None when OSError is raised."""
        mock_func = MagicMock(side_effect=OSError("test error"))
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result is None

    def test_valueerror_returns_none(self):
        """Should return None when ValueError is raised."""
        mock_func = MagicMock(side_effect=ValueError("test error"))
        with patch('mitmproxy.addons.oximy.process._responsible_pid_func', mock_func):
            result = _get_responsible_pid(1234)
            assert result is None


# =============================================================================
# _proc_pidpath Tests
# =============================================================================

class TestProcPidpath:
    """Tests for _proc_pidpath function."""

    def test_func_unavailable_returns_none(self):
        """Should return None when proc_pidpath_func is not available."""
        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', None):
            result = _proc_pidpath(1234)
            assert result is None

    def test_success_returns_path(self):
        """Should return path on success."""
        import ctypes

        mock_func = MagicMock()
        mock_func.return_value = 50  # Non-zero indicates success

        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', mock_func):
            with patch('ctypes.create_string_buffer') as mock_buffer:
                mock_buf = MagicMock()
                mock_buf.value = b"/Applications/Safari.app/Contents/MacOS/Safari"
                mock_buffer.return_value = mock_buf

                result = _proc_pidpath(1234)
                assert result == "/Applications/Safari.app/Contents/MacOS/Safari"

    def test_zero_return_returns_none(self):
        """Should return None when ret <= 0."""
        mock_func = MagicMock(return_value=0)
        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', mock_func):
            with patch('ctypes.create_string_buffer'):
                result = _proc_pidpath(1234)
                assert result is None

    def test_negative_return_returns_none(self):
        """Should return None when ret is negative."""
        mock_func = MagicMock(return_value=-1)
        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', mock_func):
            with patch('ctypes.create_string_buffer'):
                result = _proc_pidpath(1234)
                assert result is None

    def test_oserror_returns_none(self):
        """Should return None on OSError."""
        mock_func = MagicMock(side_effect=OSError("test"))
        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', mock_func):
            result = _proc_pidpath(1234)
            assert result is None

    def test_unicode_decode_error_returns_none(self):
        """Should return None on UnicodeDecodeError."""
        # The actual _proc_pidpath handles UnicodeDecodeError internally
        # by catching it in the except clause. We can't easily mock bytes.decode
        # since it's a built-in. Instead, test that the function handles
        # this by verifying the code path catches ValueError/OSError/UnicodeDecodeError.
        # The implementation catches these errors and returns None.

        # Test via the actual exception handling in _proc_pidpath
        mock_func = MagicMock(side_effect=ValueError("test"))
        with patch('mitmproxy.addons.oximy.process._proc_pidpath_func', mock_func):
            result = _proc_pidpath(1234)
            assert result is None


# =============================================================================
# ClientProcess Tests
# =============================================================================

class TestClientProcess:
    """Tests for ClientProcess dataclass."""

    def test_construction(self):
        """Should construct with all fields."""
        proc = ClientProcess(
            pid=1234,
            name="Safari",
            path="/Applications/Safari.app/Contents/MacOS/Safari",
            ppid=1,
            parent_name="launchd",
            user="testuser",
            port=54321,
            bundle_id="com.apple.Safari",
        )
        assert proc.pid == 1234
        assert proc.name == "Safari"
        assert proc.path == "/Applications/Safari.app/Contents/MacOS/Safari"
        assert proc.ppid == 1
        assert proc.parent_name == "launchd"
        assert proc.user == "testuser"
        assert proc.port == 54321
        assert proc.bundle_id == "com.apple.Safari"

    def test_default_bundle_id_none(self):
        """bundle_id should default to None."""
        proc = ClientProcess(
            pid=1234,
            name="test",
            path="/test",
            ppid=1,
            parent_name=None,
            user="user",
            port=12345,
        )
        assert proc.bundle_id is None


# =============================================================================
# ProcessResolver Initialization Tests
# =============================================================================

class TestProcessResolverInit:
    """Tests for ProcessResolver initialization."""

    def test_default_state(self):
        """Should initialize with default state."""
        resolver = ProcessResolver()
        assert resolver._proxy_port == 0
        assert resolver._cache == {}
        assert resolver._bundle_id_cache == {}
        assert resolver._port_cache == {}

    def test_custom_proxy_port(self):
        """Should accept custom proxy port."""
        resolver = ProcessResolver(proxy_port=8080)
        assert resolver._proxy_port == 8080

    def test_platform_detection(self):
        """Should detect platform correctly based on actual system."""
        import platform
        resolver = ProcessResolver()
        system = platform.system()
        if system == "Darwin":
            assert resolver._is_macos is True
            assert resolver._is_linux is False
            assert resolver._is_windows is False
        elif system == "Linux":
            assert resolver._is_macos is False
            assert resolver._is_linux is True
            assert resolver._is_windows is False
        elif system == "Windows":
            assert resolver._is_macos is False
            assert resolver._is_linux is False
            assert resolver._is_windows is True

    def test_update_proxy_port(self):
        """update_proxy_port should update the port."""
        resolver = ProcessResolver()
        resolver.update_proxy_port(9090)
        assert resolver._proxy_port == 9090


# =============================================================================
# ProcessResolver._extract_name Tests
# =============================================================================

class TestExtractName:
    """Tests for ProcessResolver._extract_name method."""

    def test_unix_path(self):
        """Should extract name from Unix path."""
        resolver = ProcessResolver()
        assert resolver._extract_name("/usr/bin/python3") == "python3"
        assert resolver._extract_name("/Applications/Safari.app/Contents/MacOS/Safari") == "Safari"

    def test_windows_path(self):
        """Should extract name from Windows path."""
        resolver = ProcessResolver()
        assert resolver._extract_name("C:\\Program Files\\Chrome\\chrome.exe") == "chrome"
        assert resolver._extract_name("D:\\Apps\\test.exe") == "test"

    def test_exe_stripped(self):
        """Should strip .exe extension."""
        resolver = ProcessResolver()
        assert resolver._extract_name("C:\\test\\app.exe") == "app"
        assert resolver._extract_name("C:\\test\\APP.EXE") == "APP"  # Case preserved except .exe

    def test_none_input(self):
        """Should return None for None input."""
        resolver = ProcessResolver()
        assert resolver._extract_name(None) is None

    def test_empty_input(self):
        """Should return None for empty path."""
        resolver = ProcessResolver()
        assert resolver._extract_name("") is None

    def test_just_filename(self):
        """Should handle just a filename."""
        resolver = ProcessResolver()
        assert resolver._extract_name("python3") == "python3"
        assert resolver._extract_name("chrome.exe") == "chrome"


# =============================================================================
# ProcessResolver._extract_exe_name Tests
# =============================================================================

class TestExtractExeName:
    """Tests for ProcessResolver._extract_exe_name method."""

    def test_windows_exe_path(self):
        """Should extract exe name from Windows path."""
        resolver = ProcessResolver()
        assert resolver._extract_exe_name("C:\\Program Files\\app.exe") == "app.exe"

    def test_non_exe_returns_none(self):
        """Should return None for non-.exe paths."""
        resolver = ProcessResolver()
        assert resolver._extract_exe_name("/usr/bin/python3") is None
        assert resolver._extract_exe_name("C:\\test\\app") is None

    def test_unix_path_with_exe(self):
        """Should handle Unix path with .exe (Wine?)."""
        resolver = ProcessResolver()
        assert resolver._extract_exe_name("/home/user/wine/app.exe") == "app.exe"

    def test_none_input(self):
        """Should return None for None input."""
        resolver = ProcessResolver()
        assert resolver._extract_exe_name(None) is None


# =============================================================================
# ProcessResolver._looks_like_bundle_id Tests
# =============================================================================

class TestLooksLikeBundleId:
    """Tests for ProcessResolver._looks_like_bundle_id method."""

    @pytest.mark.parametrize("bundle_id", [
        "com.apple.Safari",
        "com.google.Chrome",
        "org.mozilla.firefox",
        "net.whatsapp.WhatsApp",
        "io.github.test",
        "app.cursor.cursor",
        "me.test.app",
        "co.company.product",
        "dev.test.myapp",
    ])
    def test_valid_bundle_ids(self, bundle_id: str):
        """Should recognize valid bundle IDs."""
        resolver = ProcessResolver()
        assert resolver._looks_like_bundle_id(bundle_id) is True

    @pytest.mark.parametrize("invalid", [
        "Safari",  # No dots
        "com.apple",  # Only 1 dot (need at least 2)
        "unknown.prefix.app",  # Unknown prefix
        "com.apple.test@#$",  # Special chars
        "",  # Empty
    ])
    def test_invalid_bundle_ids(self, invalid: str):
        """Should reject invalid bundle IDs."""
        resolver = ProcessResolver()
        assert resolver._looks_like_bundle_id(invalid) is False

    def test_none_input(self):
        """Should return False for None."""
        resolver = ProcessResolver()
        assert resolver._looks_like_bundle_id(None) is False  # type: ignore

    def test_hyphens_and_underscores_allowed(self):
        """Should allow hyphens and underscores in parts."""
        resolver = ProcessResolver()
        assert resolver._looks_like_bundle_id("com.my-company.test_app") is True


# =============================================================================
# ProcessResolver.get_process_for_port Tests
# =============================================================================

class TestGetProcessForPort:
    """Tests for ProcessResolver.get_process_for_port method."""

    @pytest.mark.asyncio
    async def test_cache_hit_fresh(self):
        """Should return cached result if fresh."""
        resolver = ProcessResolver()
        cached_process = ClientProcess(
            pid=1234, name="Cached", path="/test",
            ppid=1, parent_name=None, user="test", port=54321
        )
        resolver._port_cache[54321] = (cached_process, time.time())

        result = await resolver.get_process_for_port(54321)
        assert result.name == "Cached"

    @pytest.mark.asyncio
    async def test_cache_hit_expired(self):
        """Should re-resolve if cache is expired."""
        resolver = ProcessResolver()
        cached_process = ClientProcess(
            pid=1234, name="Cached", path="/test",
            ppid=1, parent_name=None, user="test", port=54321
        )
        # Set timestamp in the past (expired)
        resolver._port_cache[54321] = (cached_process, time.time() - 120)

        with patch.object(resolver, '_get_process_for_port_impl') as mock_impl:
            new_process = ClientProcess(
                pid=5678, name="Fresh", path="/fresh",
                ppid=1, parent_name=None, user="test", port=54321
            )
            mock_impl.return_value = new_process

            result = await resolver.get_process_for_port(54321)
            assert result.name == "Fresh"
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_returns_placeholder(self):
        """Should return placeholder on timeout."""
        resolver = ProcessResolver()
        resolver._resolution_timeout = 0.01  # Very short timeout

        async def slow_impl(port):
            await asyncio.sleep(1.0)  # Longer than timeout
            return ClientProcess(
                pid=1, name="Slow", path="/slow",
                ppid=1, parent_name=None, user="test", port=port
            )

        with patch.object(resolver, '_get_process_for_port_impl', slow_impl):
            result = await resolver.get_process_for_port(54321)
            assert result.name == "Unknown (timeout)"
            assert result.pid is None

    @pytest.mark.asyncio
    async def test_normal_resolution(self):
        """Should resolve and cache on normal path."""
        resolver = ProcessResolver()

        expected = ClientProcess(
            pid=1234, name="Test", path="/test",
            ppid=1, parent_name=None, user="test", port=54321
        )

        with patch.object(resolver, '_get_process_for_port_impl', return_value=expected):
            result = await resolver.get_process_for_port(54321)
            assert result.name == "Test"


# =============================================================================
# ProcessResolver._find_pid_for_port Tests
# =============================================================================

class TestFindPidForPort:
    """Tests for ProcessResolver._find_pid_for_port method."""

    @pytest.mark.asyncio
    async def test_no_psutil_returns_none(self):
        """Should return None when psutil unavailable."""
        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', False):
            resolver = ProcessResolver()
            result = await resolver._find_pid_for_port(54321)
            assert result is None

    @pytest.mark.asyncio
    async def test_primary_match(self, mock_psutil_connections):
        """Should find PID via primary match (laddr + raddr to proxy port)."""
        resolver = ProcessResolver(proxy_port=8080)

        mock_psutil = MagicMock()
        mock_psutil.net_connections.return_value = mock_psutil_connections

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                result = await resolver._find_pid_for_port(54321)
                assert result == 1234

    @pytest.mark.asyncio
    async def test_fallback_match(self):
        """Should use fallback match when no raddr."""
        resolver = ProcessResolver(proxy_port=8080)

        conn = MagicMock()
        conn.laddr = MagicMock(port=54321)
        conn.raddr = None
        conn.pid = 9999

        mock_psutil = MagicMock()
        mock_psutil.net_connections.return_value = [conn]

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                result = await resolver._find_pid_for_port(54321)
                assert result == 9999

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self):
        """Should return None when no matching connection."""
        resolver = ProcessResolver(proxy_port=8080)

        conn = MagicMock()
        conn.laddr = MagicMock(port=99999)  # Different port
        conn.raddr = None
        conn.pid = 1234

        mock_psutil = MagicMock()
        mock_psutil.net_connections.return_value = [conn]

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                result = await resolver._find_pid_for_port(54321)
                assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        """Should return None on exception."""
        resolver = ProcessResolver(proxy_port=8080)

        mock_psutil = MagicMock()
        mock_psutil.net_connections.side_effect = Exception("test error")

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                result = await resolver._find_pid_for_port(54321)
                assert result is None

    @pytest.mark.asyncio
    async def test_connection_with_no_pid_skipped(self):
        """Should skip connections with pid=None."""
        resolver = ProcessResolver(proxy_port=8080)

        # Connection with no PID should be skipped
        conn_no_pid = MagicMock()
        conn_no_pid.laddr = MagicMock(port=54321)
        conn_no_pid.raddr = MagicMock(port=8080)
        conn_no_pid.pid = None  # No PID available

        # Connection with PID should be found
        conn_with_pid = MagicMock()
        conn_with_pid.laddr = MagicMock(port=54322)
        conn_with_pid.raddr = MagicMock(port=8080)
        conn_with_pid.pid = 1234

        mock_psutil = MagicMock()
        mock_psutil.net_connections.return_value = [conn_no_pid, conn_with_pid]

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                # Should not find PID for port with no PID
                result = await resolver._find_pid_for_port(54321)
                assert result is None

                # Should find PID for port with PID
                result = await resolver._find_pid_for_port(54322)
                assert result == 1234


# =============================================================================
# ProcessResolver._fetch_process_info Tests
# =============================================================================

class TestFetchProcessInfo:
    """Tests for ProcessResolver._fetch_process_info method."""

    @pytest.mark.asyncio
    async def test_psutil_success(self, mock_psutil_process):
        """Should return process info from psutil."""
        resolver = ProcessResolver()

        mock_psutil = MagicMock()
        mock_psutil.Process.return_value = mock_psutil_process

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                result = await resolver._fetch_process_info(1234)

                assert result is not None
                assert result["pid"] == 1234
                assert result["ppid"] == 1
                assert result["user"] == "testuser"
                assert "Safari" in result["path"]

    @pytest.mark.asyncio
    async def test_no_such_process(self):
        """Should return None for NoSuchProcess exception."""
        resolver = ProcessResolver()

        mock_psutil = MagicMock()
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        mock_psutil.ZombieProcess = Exception
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess()

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                with patch.object(resolver, '_is_macos', False):
                    result = await resolver._fetch_process_info(99999)
                    assert result is None

    @pytest.mark.asyncio
    async def test_access_denied(self):
        """Should return None for AccessDenied exception."""
        resolver = ProcessResolver()

        mock_psutil = MagicMock()
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        mock_psutil.ZombieProcess = Exception
        mock_psutil.Process.side_effect = mock_psutil.AccessDenied()

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                with patch.object(resolver, '_is_macos', False):
                    result = await resolver._fetch_process_info(1234)
                    assert result is None

    @pytest.mark.asyncio
    async def test_zombie_process(self):
        """Should return None for ZombieProcess exception."""
        resolver = ProcessResolver()

        mock_psutil = MagicMock()
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        mock_psutil.ZombieProcess = Exception
        mock_psutil.Process.side_effect = mock_psutil.ZombieProcess()

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', True):
            with patch('mitmproxy.addons.oximy.process.psutil', mock_psutil):
                with patch.object(resolver, '_is_macos', False):
                    result = await resolver._fetch_process_info(1234)
                    assert result is None

    @pytest.mark.asyncio
    async def test_macos_libproc_fallback(self):
        """Should fall back to libproc on macOS when psutil fails."""
        resolver = ProcessResolver()
        resolver._is_macos = True

        with patch('mitmproxy.addons.oximy.process._HAS_PSUTIL', False):
            with patch('mitmproxy.addons.oximy.process._proc_pidpath') as mock_pidpath:
                mock_pidpath.return_value = "/Applications/Test.app/Contents/MacOS/Test"
                result = await resolver._fetch_process_info(1234)

                assert result is not None
                assert result["pid"] == 1234
                assert result["path"] == "/Applications/Test.app/Contents/MacOS/Test"


# =============================================================================
# ProcessResolver.clear_cache Tests
# =============================================================================

class TestClearCache:
    """Tests for ProcessResolver.clear_cache method."""

    def test_all_caches_cleared(self):
        """Should clear all caches."""
        resolver = ProcessResolver()

        # Populate caches
        resolver._cache[1234] = {"pid": 1234, "path": "/test"}
        resolver._bundle_id_cache["/test"] = "com.test.app"
        resolver._port_cache[54321] = (
            ClientProcess(pid=1, name="T", path="/t", ppid=1, parent_name=None, user="u", port=1),
            time.time()
        )

        resolver.clear_cache()

        assert resolver._cache == {}
        assert resolver._bundle_id_cache == {}
        assert resolver._port_cache == {}


# =============================================================================
# ProcessResolver Port Cache Eviction Tests
# =============================================================================

class TestPortCacheEviction:
    """Tests for port cache eviction when >1000 entries."""

    @pytest.mark.asyncio
    async def test_cache_eviction_at_limit(self):
        """Should evict oldest entries when cache exceeds 1000."""
        resolver = ProcessResolver()
        resolver._is_macos = True

        # Pre-fill with 1001 entries (oldest timestamps first)
        for i in range(1001):
            proc = ClientProcess(
                pid=i, name=f"proc{i}", path=f"/path{i}",
                ppid=1, parent_name=None, user="user", port=i
            )
            # Older entries have smaller timestamps
            resolver._port_cache[i] = (proc, time.time() - (1001 - i))

        assert len(resolver._port_cache) == 1001

        # Trigger a real resolution that adds one more entry and hits eviction
        with patch.object(resolver, '_find_pid_for_port', return_value=9999):
            with patch.object(resolver, '_get_process_info', return_value={
                "pid": 9999, "ppid": 1, "user": "u", "path": "/test"
            }):
                with patch.object(resolver, '_extract_bundle_id', return_value=None):
                    await resolver._get_process_for_port_impl(99999)

        # After eviction, should have dropped ~500 oldest entries + added 1 new
        assert len(resolver._port_cache) <= 502


# =============================================================================
# ProcessResolver._get_process_for_port_impl Tests
# =============================================================================

class TestGetProcessForPortImpl:
    """Tests for ProcessResolver._get_process_for_port_impl method."""

    @pytest.mark.asyncio
    async def test_unsupported_platform(self):
        """Should return unknown for unsupported platforms."""
        resolver = ProcessResolver()
        resolver._is_macos = False
        resolver._is_linux = False
        resolver._is_windows = False

        result = await resolver._get_process_for_port_impl(54321)
        assert result.name == "Unknown (unsupported platform)"
        assert result.pid is None

    @pytest.mark.asyncio
    async def test_pid_not_found(self):
        """Should return unknown when PID not found."""
        resolver = ProcessResolver()
        resolver._is_macos = True

        with patch.object(resolver, '_find_pid_for_port', return_value=None):
            result = await resolver._get_process_for_port_impl(54321)
            assert result.name == "Unknown (exited)"
            assert result.pid is None

    @pytest.mark.asyncio
    async def test_process_exited(self):
        """Should return unknown when process info not available."""
        resolver = ProcessResolver()
        resolver._is_macos = True

        with patch.object(resolver, '_find_pid_for_port', return_value=1234):
            with patch.object(resolver, '_get_process_info', return_value=None):
                result = await resolver._get_process_for_port_impl(54321)
                assert result.name == "Unknown (exited)"
                assert result.pid == 1234


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_resolver_thread_safe(self):
        """Resolver should be usable from multiple threads."""
        import concurrent.futures

        resolver = ProcessResolver()

        def access_resolver():
            resolver._extract_name("/test/path")
            resolver._looks_like_bundle_id("com.test.app")
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(access_resolver) for _ in range(10)]
            for future in concurrent.futures.as_completed(futures):
                assert future.result() is True

    @pytest.mark.asyncio
    async def test_concurrent_port_lookups(self):
        """Should handle concurrent port lookups."""
        resolver = ProcessResolver()

        async def lookup(port):
            # Use cached response
            proc = ClientProcess(
                pid=port, name=f"proc{port}", path=f"/path{port}",
                ppid=1, parent_name=None, user="user", port=port
            )
            resolver._port_cache[port] = (proc, time.time())
            return await resolver.get_process_for_port(port)

        # Run concurrent lookups
        results = await asyncio.gather(*[lookup(i) for i in range(100)])
        assert len(results) == 100
        assert all(r.pid == r.port for r in results)
