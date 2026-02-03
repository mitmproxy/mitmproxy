"""
Oximy addon for mitmproxy.

Captures AI API traffic with whitelist/blacklist filtering.
Supports: HTTP/REST, SSE, WebSocket, HTTP/2, HTTP/3, gRPC

Pipeline: Passthrough → Whitelist → Blacklist → Capture to JSONL
"""

from __future__ import annotations

import atexit
import fnmatch
import gzip
import json
import logging
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import IO
import urllib.error
import urllib.request
from urllib.parse import urlparse

from mitmproxy import connection, ctx, http, tls

# Create urllib opener that bypasses system proxy settings.
# This is critical: when Mac app enables system proxy pointing to mitmproxy,
# the addon's own API calls would loop through itself without this bypass.
_no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

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

# =============================================================================
# CENTRALIZED PATHS - All file paths derive from OXIMY_DIR
# =============================================================================
OXIMY_DIR = Path(os.environ.get("OXIMY_HOME", "~/.oximy")).expanduser()
OXIMY_TRACES_DIR = OXIMY_DIR / "traces"
OXIMY_CONFIG_FILE = OXIMY_DIR / "config.json"
OXIMY_STATE_FILE = OXIMY_DIR / "remote-state.json"
OXIMY_COMMAND_RESULTS_FILE = OXIMY_DIR / "command-results.json"
OXIMY_TOKEN_FILE = OXIMY_DIR / "device-token"
OXIMY_UPLOAD_STATE_FILE = OXIMY_DIR / "upload-state.json"
OXIMY_PASSTHROUGH_CACHE = OXIMY_DIR / "learned-passthrough.json"
OXIMY_FORCE_SYNC_TRIGGER = OXIMY_DIR / "force-sync"
OXIMY_SENSOR_CONFIG_CACHE = OXIMY_DIR / "sensor-config.json"
OXIMY_PROXY_PORT_FILE = OXIMY_DIR / "proxy-port"
OXIMY_ENV_SCRIPT = OXIMY_DIR / "oximy_env.sh"
OXIMY_COMBINED_CA_BUNDLE = OXIMY_DIR / "combined-ca-bundle.pem"
OXIMY_CA_CERT = OXIMY_DIR / "oximy-ca-cert.pem"

# Shell profile markers for idempotent injection/removal
_SHELL_MARKER = "# --- Oximy (do not edit this block) ---"
_SHELL_END_MARKER = "# --- End Oximy ---"

# Maximum bytes to accumulate from streamed (SSE) responses before stopping capture
_MAX_STREAM_CAPTURE_BYTES = 100 * 1024 * 1024  # 100 MB

# =============================================================================
# WINDOWS BROWSER DETECTION
# =============================================================================
# Windows browser executables - treated as browsers ("host" type)
# On Windows, bundle_id is the exe name, so we need to recognize common browsers
WINDOWS_BROWSERS = frozenset({
    "chrome.exe", "msedge.exe", "firefox.exe",
    "brave.exe", "opera.exe", "vivaldi.exe",
})

# =============================================================================
# SENSOR STATE MANAGEMENT
# =============================================================================
# Debounce prevents rapid on/off from network glitches (2 poll cycles at 3s interval)
SENSOR_DEBOUNCE_SECONDS = 6.0


class _SensorState:
    """Thread-safe sensor state management.

    Consolidates all mutable global state into a single class with proper locking.
    """

    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock - allows nested acquisition
        self.previous_sensor_enabled: bool | None = None  # Detect state changes
        self.proxy_port: str | None = None  # Actual proxy port once configured
        self.sensor_active: bool = True  # Master switch - when False, all hooks return immediately
        self.pending_state: bool | None = None  # Pending state change waiting for debounce
        self.pending_since: float = 0.0  # Timestamp when pending state was first seen
        self.previous_force_sync: bool = False  # Detect false→true transitions (one-shot trigger)
        self.previous_force_logout: bool = False  # Detect false→true transitions (one-shot trigger)
        self.proxy_active: bool = False  # System proxy is actively configured

    @property
    def lock(self) -> threading.RLock:
        return self._lock


_state = _SensorState()

# Legacy aliases for backwards compatibility during transition
_globals_lock = _state.lock

# Command execution results tracking - populated by _parse_sensor_config()
# and consumed by desktop apps for heartbeat reporting
_command_results: dict[str, dict[str, str | bool | None]] = {}

# Track executed commands to prevent re-execution when using cached config
# Commands like force_sync should only execute once, not on every config poll
_executed_command_hashes: set[str] = set()

# Track 401 errors and force_logout state
_consecutive_401_count: int = 0
_force_logout_triggered: bool = False
_MAX_401_RETRIES: int = 5  # Wait for 5 consecutive 401s before triggering logout


def _get_command_hash(command_name: str) -> str:
    """Generate a unique hash for a command to track execution."""
    return f"{command_name}:executed"


def _write_force_logout_state() -> None:
    """Write force_logout=true to remote-state.json for Swift to pick up.

    Called when we detect an invalid device token (401 error) so the app
    will log out and prompt for re-enrollment.
    """
    try:
        state_data = {
            "sensor_enabled": False,
            "force_logout": True,
            "proxy_active": False,
            "proxy_port": None,
            "tenantId": None,
            "itSupport": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "appConfig": None,
        }
        OXIMY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OXIMY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        logger.info("Force logout state written to remote-state.json")
    except (IOError, OSError) as e:
        logger.warning(f"Failed to write force logout state: {e}")


def _get_network_services() -> list[str]:
    """Get list of active network services (Wi-Fi, Ethernet, etc.)."""
    if sys.platform != "darwin":
        return []
    try:
        result = subprocess.run(
            ["networksetup", "-listallnetworkservices"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return ["Wi-Fi"]  # Fallback
        services = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            line = line.strip()
            if line and not line.startswith("*"):  # Skip disabled services
                services.append(line)
        return services if services else ["Wi-Fi"]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug(f"Could not list network services: {e}")
        return ["Wi-Fi"]  # Fallback


# =============================================================================
# SYSTEM PROXY
# =============================================================================

def _set_system_proxy(enable: bool) -> None:
    """Enable or disable system proxy settings (cross-platform)."""
    if sys.platform == "darwin":
        _set_macos_proxy(enable)
    elif sys.platform == "win32":
        _set_windows_proxy(enable)


def _set_windows_proxy(enable: bool) -> bool:
    """Enable or disable Windows system proxy via registry. Returns success status."""
    reg_path = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    try:
        if enable:
            if not _state.proxy_port:
                logger.debug("Cannot enable Windows proxy: port not configured yet")
                return False
            proxy_server = f"{PROXY_HOST}:{_state.proxy_port}"

            # Set both values
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "1", "/f"],
                           check=True, capture_output=True)
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyServer", "/t", "REG_SZ", "/d", proxy_server, "/f"],
                           check=True, capture_output=True)

            # Verify the setting was applied
            result = subprocess.run(["reg", "query", reg_path, "/v", "ProxyEnable"],
                                    capture_output=True, text=True)
            if "0x1" in result.stdout:
                logger.info(f"Windows proxy enabled: {proxy_server}")
                return True
            else:
                logger.warning("Windows proxy registry set but verification failed")
                return False
        else:
            # Always try to disable, even if we think it's already disabled
            subprocess.run(["reg", "add", reg_path, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "0", "/f"],
                           check=True, capture_output=True)
            logger.info("Windows proxy disabled")
            return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to set Windows proxy: {e}")
        return False


def _set_macos_proxy(enable: bool) -> None:
    """Enable or disable macOS system proxy for all network services."""
    services = _get_network_services()

    if enable and not _state.proxy_port:
        logger.warning("Cannot enable macOS proxy: port not configured")
        return

    for service in services:
        try:
            if enable:
                subprocess.run(["networksetup", "-setsecurewebproxy", service, PROXY_HOST, _state.proxy_port],
                               check=True, capture_output=True)
                subprocess.run(["networksetup", "-setwebproxy", service, PROXY_HOST, _state.proxy_port],
                               check=True, capture_output=True)
            else:
                subprocess.run(["networksetup", "-setsecurewebproxystate", service, "off"],
                               check=True, capture_output=True)
                subprocess.run(["networksetup", "-setwebproxystate", service, "off"],
                               check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Could not set proxy for {service}: {e}")

    if enable:
        logger.info(f"macOS proxy enabled: {PROXY_HOST}:{_state.proxy_port} on {services}")
    else:
        logger.info(f"macOS proxy disabled on {services}")


def _clear_local_cache() -> None:
    """Delete all trace files and reset upload state."""
    traces_dir = OXIMY_TRACES_DIR
    upload_state = OXIMY_UPLOAD_STATE_FILE

    deleted_count = 0
    if traces_dir.exists():
        for f in traces_dir.glob("*.jsonl"):
            try:
                f.unlink()
                deleted_count += 1
            except (IOError, OSError) as e:
                logger.debug(f"Could not delete {f}: {e}")

    if upload_state.exists():
        try:
            upload_state.unlink()
        except (IOError, OSError) as e:
            logger.debug(f"Could not delete upload state: {e}")

    logger.info(f"Local cache cleared: {deleted_count} trace files deleted")


# =============================================================================
# CLEANUP SAFETY NET
# =============================================================================

_cleanup_done = False
_addon_manages_proxy = False  # Tracks if addon enabled system proxy (for cleanup)


def _atomic_write(target: Path, content: str, mode: int = 0o600) -> None:
    """Atomically write content to target file with restricted permissions.

    Writes to a temp file in the same directory then renames (atomic on POSIX).
    This prevents corruption if the process is killed mid-write.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.")
    closed = False
    try:
        os.write(fd, content.encode("utf-8"))
        if sys.platform != "win32":
            os.fchmod(fd, mode)
        os.close(fd)
        closed = True
        os.replace(tmp, str(target))
    except BaseException:
        if not closed:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_proxy_port_file(port: str) -> None:
    """Write proxy port to file for terminal env script discovery."""
    try:
        _atomic_write(OXIMY_PROXY_PORT_FILE, port)
        logger.debug(f"Proxy port file written: {port}")
    except (IOError, OSError) as e:
        logger.warning(f"Failed to write proxy port file: {e}")


def _delete_proxy_port_file() -> None:
    """Delete proxy port file on shutdown so terminal env script deactivates."""
    try:
        if OXIMY_PROXY_PORT_FILE.exists():
            OXIMY_PROXY_PORT_FILE.unlink()
            logger.debug("Proxy port file deleted")
    except (IOError, OSError) as e:
        logger.warning(f"Failed to delete proxy port file: {e}")


# =============================================================================
# TERMINAL ENVIRONMENT SETUP
# =============================================================================

def _setup_terminal_env() -> None:
    """Write env script, generate combined CA bundle, and inject shell profiles.

    Idempotent — safe to call on every startup. Shell profile injection is
    skipped if the marker block already exists.
    """
    try:
        _write_env_script()
        _generate_combined_ca_bundle()
        if sys.platform == "darwin":
            _inject_shell_profiles([
                Path.home() / ".zshrc",
                Path.home() / ".bashrc",
            ])
        elif sys.platform == "win32":
            _write_windows_env_scripts()
            _inject_powershell_profiles()
            _inject_cmd_autorun()
    except Exception as e:
        logger.warning(f"Terminal env setup failed (non-fatal): {e}")


def _write_env_script() -> None:
    """Write the shell env script sourced by ~/.zshrc to set proxy + CA trust vars."""
    script = """\
# Auto-generated by Oximy. Do not edit.
# Sourced by shell profile to route terminal traffic through Oximy proxy.

# --- Cleanup function: unset all Oximy proxy/CA env vars ---
_oximy_cleanup() {
    unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
    unset NO_PROXY no_proxy
    unset NODE_EXTRA_CA_CERTS SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE
    unset OXIMY_PROXY_ACTIVE
}

# --- Pre-command hook: auto-unset vars when proxy is gone ---
_oximy_check() {
    if [ -n "$OXIMY_PROXY_ACTIVE" ] && [ ! -f "$HOME/.oximy/proxy-port" ]; then
        _oximy_cleanup
    fi
}

# Install the check hook (works in both zsh and bash)
if [ -n "$ZSH_VERSION" ]; then
    autoload -Uz add-zsh-hook 2>/dev/null
    if typeset -f add-zsh-hook >/dev/null 2>&1; then
        add-zsh-hook precmd _oximy_check
    fi
elif [ -n "$BASH_VERSION" ]; then
    case "$PROMPT_COMMAND" in
        *_oximy_check*) ;;  # already installed
        "") PROMPT_COMMAND="_oximy_check" ;;
        *)  PROMPT_COMMAND="_oximy_check;$PROMPT_COMMAND" ;;
    esac
fi

# --- Set proxy vars (only if proxy is currently running) ---
_oximy_port_file="$HOME/.oximy/proxy-port"
if [ ! -f "$_oximy_port_file" ]; then
    _oximy_cleanup
    unset _oximy_port_file
    return 0
fi
_oximy_port=$(cat "$_oximy_port_file" 2>/dev/null)
if [ -z "$_oximy_port" ]; then
    _oximy_cleanup
    unset _oximy_port_file _oximy_port
    return 0
fi

_oximy_ca="$HOME/.oximy/combined-ca-bundle.pem"
[ ! -f "$_oximy_ca" ] && { unset _oximy_port_file _oximy_port _oximy_ca; return 0; }

# Proxy routing (both cases — curl uses lowercase, most libraries use uppercase)
export HTTP_PROXY="http://127.0.0.1:${_oximy_port}"
export HTTPS_PROXY="http://127.0.0.1:${_oximy_port}"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export NO_PROXY="localhost,127.0.0.1,::1,.local"
export no_proxy="$NO_PROXY"

# Node.js — NODE_EXTRA_CA_CERTS appends to built-in CAs (no combined bundle needed)
export NODE_EXTRA_CA_CERTS="$HOME/.oximy/oximy-ca-cert.pem"

# Python (requests, httpx, urllib3), Ruby, Go, general OpenSSL — these REPLACE the
# default CA store, so a combined bundle (system CAs + Oximy CA) is required.
export SSL_CERT_FILE="$_oximy_ca"
export REQUESTS_CA_BUNDLE="$_oximy_ca"

# curl
export CURL_CA_BUNDLE="$_oximy_ca"

# Sentinel so the precmd hook knows vars were set
export OXIMY_PROXY_ACTIVE=1

unset _oximy_port_file _oximy_port _oximy_ca
"""
    _atomic_write(OXIMY_ENV_SCRIPT, script, mode=0o644)
    logger.debug("Terminal env script written")


def _generate_combined_ca_bundle() -> None:
    """Build PEM bundle: system root CAs + Oximy CA.

    Required because SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE replace
    (not append to) the default CA store.
    """
    if not OXIMY_CA_CERT.exists():
        logger.debug("Oximy CA cert not found, skipping combined bundle generation")
        return

    oximy_ca = OXIMY_CA_CERT.read_text(encoding="utf-8")
    parts: list[str] = []

    if sys.platform == "darwin":
        # Export macOS system root certificates
        for keychain in (
            "/System/Library/Keychains/SystemRootCertificates.keychain",
            "/Library/Keychains/System.keychain",
        ):
            try:
                result = subprocess.run(
                    ["security", "find-certificate", "-a", "-p", keychain],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts.append(result.stdout)
            except (subprocess.SubprocessError, OSError):
                pass
    elif sys.platform == "win32":
        # Export Windows system root CAs via PowerShell
        try:
            result = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-Command",
                    "Get-ChildItem -Path Cert:\\LocalMachine\\Root | ForEach-Object { "
                    "'-----BEGIN CERTIFICATE-----'; "
                    "[Convert]::ToBase64String($_.RawData, 'InsertLineBreaks'); "
                    "'-----END CERTIFICATE-----'; '' }",
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts.append(result.stdout)
        except (subprocess.SubprocessError, OSError):
            pass

    parts.append(oximy_ca)
    _atomic_write(OXIMY_COMBINED_CA_BUNDLE, "\n".join(parts))
    logger.debug("Combined CA bundle generated")


def _inject_shell_profiles(profiles: list[Path]) -> None:
    """Inject source line into shell profiles (macOS: .zshrc, .bashrc)."""
    injection = (
        f"\n{_SHELL_MARKER}\n"
        f'[ -f "$HOME/.oximy/oximy_env.sh" ] && . "$HOME/.oximy/oximy_env.sh"\n'
        f"{_SHELL_END_MARKER}\n"
    )

    for profile in profiles:
        try:
            content = profile.read_text(encoding="utf-8") if profile.exists() else ""

            # Idempotent
            if _SHELL_MARKER in content:
                continue

            if content and not content.endswith("\n"):
                content += "\n"
            content += injection

            _atomic_write(profile, content, mode=profile.stat().st_mode & 0o7777 if profile.exists() else 0o644)
            logger.info(f"Injected shell profile: {profile.name}")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to inject {profile.name}: {e}")


def _write_windows_env_scripts() -> None:
    """Write PowerShell and CMD env scripts for Windows."""
    ps1 = r"""# Auto-generated by Oximy. Do not edit.
$portFile = Join-Path $env:USERPROFILE '.oximy\proxy-port'
if (-not (Test-Path $portFile)) { return }
$port = (Get-Content $portFile -Raw).Trim()
if ([string]::IsNullOrEmpty($port)) { return }
$caBundle = Join-Path $env:USERPROFILE '.oximy\combined-ca-bundle.pem'
if (-not (Test-Path $caBundle)) { return }
$caCert = Join-Path $env:USERPROFILE '.oximy\oximy-ca-cert.pem'
$env:HTTP_PROXY = "http://127.0.0.1:$port"
$env:HTTPS_PROXY = "http://127.0.0.1:$port"
$env:http_proxy = $env:HTTP_PROXY
$env:https_proxy = $env:HTTPS_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:no_proxy = $env:NO_PROXY
$env:NODE_EXTRA_CA_CERTS = $caCert
$env:SSL_CERT_FILE = $caBundle
$env:REQUESTS_CA_BUNDLE = $caBundle
$env:CURL_CA_BUNDLE = $caBundle
"""
    _atomic_write(OXIMY_DIR / "oximy_env.ps1", ps1, mode=0o644)

    cmd = r"""@echo off
REM Auto-generated by Oximy. Do not edit.
set "OXIMY_PORT_FILE=%USERPROFILE%\.oximy\proxy-port"
if not exist "%OXIMY_PORT_FILE%" goto :eof
set /p OXIMY_PORT=<"%OXIMY_PORT_FILE%"
if "%OXIMY_PORT%"=="" goto :eof
set "OXIMY_CA=%USERPROFILE%\.oximy\combined-ca-bundle.pem"
if not exist "%OXIMY_CA%" goto :eof
set "OXIMY_CERT=%USERPROFILE%\.oximy\oximy-ca-cert.pem"
set "HTTP_PROXY=http://127.0.0.1:%OXIMY_PORT%"
set "HTTPS_PROXY=http://127.0.0.1:%OXIMY_PORT%"
set "http_proxy=%HTTP_PROXY%"
set "https_proxy=%HTTPS_PROXY%"
set "NO_PROXY=localhost,127.0.0.1,::1"
set "no_proxy=%NO_PROXY%"
set "NODE_EXTRA_CA_CERTS=%OXIMY_CERT%"
set "SSL_CERT_FILE=%OXIMY_CA%"
set "REQUESTS_CA_BUNDLE=%OXIMY_CA%"
set "CURL_CA_BUNDLE=%OXIMY_CA%"
set "OXIMY_PORT_FILE="
set "OXIMY_PORT="
set "OXIMY_CA="
set "OXIMY_CERT="
"""
    _atomic_write(OXIMY_DIR / "oximy_env.cmd", cmd, mode=0o644)
    logger.debug("Windows env scripts written")


def _inject_powershell_profiles() -> None:
    """Inject dot-source into PowerShell profiles (5.1 + Core 7)."""
    docs = Path.home() / "Documents"
    ps1_path = str(OXIMY_DIR / "oximy_env.ps1")
    injection = (
        f"\n{_SHELL_MARKER}\n"
        f"if (Test-Path '{ps1_path}') {{ . '{ps1_path}' }}\n"
        f"{_SHELL_END_MARKER}\n"
    )

    for profile in (
        docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
    ):
        try:
            profile.parent.mkdir(parents=True, exist_ok=True)
            content = profile.read_text(encoding="utf-8") if profile.exists() else ""
            if _SHELL_MARKER in content:
                continue
            if content and not content.endswith("\n"):
                content += "\n"
            content += injection
            _atomic_write(profile, content, mode=0o644)
            logger.info(f"Injected PowerShell profile: {profile}")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to inject PowerShell profile {profile}: {e}")


def _inject_cmd_autorun() -> None:
    """Set CMD AutoRun registry value to source oximy_env.cmd on every cmd.exe launch."""
    try:
        import winreg  # noqa: F811
        cmd_path = str(OXIMY_DIR / "oximy_env.cmd")
        key_path = r"Software\Microsoft\Command Processor"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                existing, _ = winreg.QueryValueEx(key, "AutoRun")
            except FileNotFoundError:
                existing = ""

            if cmd_path.lower() in (existing or "").lower():
                return  # Already injected

            new_value = f'"{cmd_path}"' if not existing else f'{existing} & "{cmd_path}"'
            winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_SZ, new_value)
            logger.info(f"Injected CMD AutoRun: {new_value}")
    except Exception as e:
        logger.debug(f"CMD AutoRun injection skipped: {e}")


def _teardown_terminal_env() -> None:
    """Remove shell profile injections and generated files on shutdown."""
    try:
        if sys.platform == "darwin":
            _remove_shell_profile_injections([
                Path.home() / ".zshrc",
                Path.home() / ".bashrc",
            ])
        elif sys.platform == "win32":
            docs = Path.home() / "Documents"
            _remove_shell_profile_injections([
                docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
                docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
            ])
            _remove_cmd_autorun()

        # Remove generated env scripts and CA bundle
        for path in (OXIMY_ENV_SCRIPT, OXIMY_COMBINED_CA_BUNDLE,
                      OXIMY_DIR / "oximy_env.ps1", OXIMY_DIR / "oximy_env.cmd"):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Terminal env teardown failed (non-fatal): {e}")


def _remove_shell_profile_injections(profiles: list[Path]) -> None:
    """Remove the Oximy marker block from shell profiles."""
    for profile in profiles:
        try:
            if not profile.exists():
                continue
            content = profile.read_text(encoding="utf-8")
            if _SHELL_MARKER not in content:
                continue

            start = content.find(_SHELL_MARKER)
            end = content.find(_SHELL_END_MARKER)
            if start < 0 or end < 0:
                continue

            remove_end = end + len(_SHELL_END_MARKER)
            # Consume surrounding newlines
            if start > 0 and content[start - 1] == "\n":
                start -= 1
            if remove_end < len(content) and content[remove_end] == "\n":
                remove_end += 1

            content = content[:start] + content[remove_end:]
            _atomic_write(profile, content, mode=profile.stat().st_mode & 0o7777)
            logger.info(f"Removed shell profile injection: {profile.name}")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to remove injection from {profile.name}: {e}")


def _remove_cmd_autorun() -> None:
    """Remove Oximy entry from CMD AutoRun registry value."""
    try:
        import winreg
        cmd_path = str(OXIMY_DIR / "oximy_env.cmd")
        key_path = r"Software\Microsoft\Command Processor"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                existing, _ = winreg.QueryValueEx(key, "AutoRun")
            except FileNotFoundError:
                return

            if not existing or cmd_path.lower() not in existing.lower():
                return

            cleaned = existing
            for pattern in (f' & "{cmd_path}"', f'"{cmd_path}" & ', f'"{cmd_path}"'):
                cleaned = cleaned.replace(pattern, "")
            cleaned = cleaned.strip()

            if not cleaned:
                winreg.DeleteValue(key, "AutoRun")
            else:
                winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_SZ, cleaned)
            logger.info("Removed CMD AutoRun injection")
    except Exception as e:
        logger.debug(f"CMD AutoRun removal skipped: {e}")


def _write_proxy_state() -> None:
    """Write current proxy state to remote-state.json for Swift app."""
    try:
        # Read existing state if present
        existing = {}
        if OXIMY_STATE_FILE.exists():
            with open(OXIMY_STATE_FILE, encoding="utf-8") as f:
                existing = json.load(f)

        # Update proxy status
        existing["proxy_active"] = _state.proxy_active
        existing["proxy_port"] = _state.proxy_port
        existing["timestamp"] = datetime.now(timezone.utc).isoformat()

        OXIMY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OXIMY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        logger.debug(f"Proxy state written: active={_state.proxy_active}, port={_state.proxy_port}")
    except (IOError, OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to write proxy state: {e}")


def _emergency_cleanup() -> None:
    """Emergency cleanup - disable proxy even if mitmproxy crashes."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    # ALWAYS try to disable proxy on Windows, regardless of _addon_manages_proxy
    # This is defensive - better to disable twice than leave proxy orphaned
    logger.info("Emergency cleanup: disabling system proxy...")
    _set_system_proxy(enable=False)
    _delete_proxy_port_file()
    with _state.lock:
        _state.proxy_active = False
    _write_proxy_state()


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
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Could not verify certificate trust: {e}")
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

# Support environment variable overrides for testing/CI
DEFAULT_SENSOR_CONFIG_URL = os.environ.get(
    "OXIMY_CONFIG_URL",
    "https://api.oximy.com/api/v1/sensor-config"
)
DEFAULT_SENSOR_CONFIG_CACHE = os.environ.get(
    "OXIMY_CONFIG_CACHE",
    str(OXIMY_SENSOR_CONFIG_CACHE)
)
DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS = int(os.environ.get(
    "OXIMY_CONFIG_REFRESH_INTERVAL",
    "3"  # 3 seconds for real-time sensor control
))


def fetch_sensor_config(
    url: str = DEFAULT_SENSOR_CONFIG_URL,
    cache_path: str = DEFAULT_SENSOR_CONFIG_CACHE,
    addon_instance=None,
) -> dict:
    """Fetch sensor config from API and cache locally.

    Args:
        url: Sensor config API URL
        cache_path: Local cache file path
        addon_instance: Optional Oximy addon instance for command execution
    """
    cache_file = Path(cache_path).expanduser()

    default_config = {
        "whitelist": [],
        "blacklist": [],
        "passthrough": [],
    }

    # Read device token from file (written by Swift app)
    token = None
    if OXIMY_TOKEN_FILE.exists():
        try:
            token = OXIMY_TOKEN_FILE.read_text().strip()
            if token:
                logger.debug("Device token loaded for authenticated request")
        except (IOError, OSError) as e:
            logger.debug(f"Could not read device token: {e}")

    try:
        logger.info(f"Fetching sensor config from {url}")
        headers = {"User-Agent": "Oximy-Sensor/1.0", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with _no_proxy_opener.open(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        # Cache the raw response locally
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        logger.info(f"Sensor config cached to {cache_file}")

        # Clear executed commands on fresh API fetch - allows commands to re-execute
        # when they appear in a new API response (vs repeated execution from cache)
        global _executed_command_hashes, _consecutive_401_count, _force_logout_triggered
        _executed_command_hashes.clear()
        _consecutive_401_count = 0  # Reset 401 counter on successful fetch
        _force_logout_triggered = False  # Reset logout flag so it can trigger again if needed

        return _parse_sensor_config(raw, addon_instance)

    except urllib.error.HTTPError as e:
        # Handle 401 specifically - invalid device token requires logout after retries
        if e.code == 401:
            # Note: _force_logout_triggered and _consecutive_401_count already declared global above
            _consecutive_401_count += 1
            logger.warning(f"Device token invalid (401) - attempt {_consecutive_401_count}/{_MAX_401_RETRIES}")

            if _consecutive_401_count >= _MAX_401_RETRIES and not _force_logout_triggered:
                _force_logout_triggered = True
                logger.warning(f"Max 401 retries ({_MAX_401_RETRIES}) reached - triggering force_logout for re-enrollment")
                _write_force_logout_state()
            elif _force_logout_triggered:
                logger.debug("401 error but force_logout already triggered")

            # Don't use cache with invalid token - return empty config
            return default_config
        else:
            # Non-401 HTTP errors: log and fall through to cache
            logger.warning(f"Failed to fetch sensor config: HTTP {e.code}")
            # Fall through to cache fallback below

        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info(f"Using cached sensor config from {cache_file}")
                return _parse_sensor_config(cached, addon_instance)
            except (json.JSONDecodeError, IOError) as cache_err:
                logger.warning(f"Failed to load cached config: {cache_err}")

        logger.warning("Using empty default config")
        return default_config

    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to fetch sensor config: {e}")

        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info(f"Using cached sensor config from {cache_file}")
                return _parse_sensor_config(cached, addon_instance)
            except (json.JSONDecodeError, IOError) as cache_err:
                logger.warning(f"Failed to load cached config: {cache_err}")

        logger.warning("Using empty default config")
        return default_config


def _apply_sensor_state(enabled: bool, addon_instance=None) -> None:
    """Apply sensor state change - enables or disables all interception.

    When disabling:
    - Sets _state.sensor_active = False (stops all hook processing)
    - Disables system proxy
    - Flushes pending traces to cloud

    When enabling:
    - Sets _state.sensor_active = True (resumes hook processing)
    - Enables system proxy
    """
    global _addon_manages_proxy

    with _state.lock:
        if enabled:
            logger.info("===== SENSOR ENABLED - Resuming all interception =====")
            _state.sensor_active = True
            # Only try to enable proxy if port is configured (running() will handle it otherwise)
            if _state.proxy_port:
                _set_system_proxy(enable=True)
                _addon_manages_proxy = True  # Track that we enabled proxy (for cleanup)
                _state.proxy_active = True
                _write_proxy_state()
        else:
            logger.info("===== SENSOR DISABLED - Stopping all interception =====")
            _state.sensor_active = False
            _set_system_proxy(enable=False)
            _state.proxy_active = False
            _write_proxy_state()

            # Flush pending traces before going quiet
            if addon_instance and addon_instance._direct_uploader:
                try:
                    uploaded = addon_instance._direct_uploader.upload_all()
                    if uploaded > 0:
                        logger.info(f"Flushed {uploaded} traces before sensor disable")
                except Exception as e:
                    logger.warning(f"Failed to flush traces on sensor disable: {e}")

        _state.previous_sensor_enabled = enabled


def _post_command_results_immediate(command_results: dict) -> None:
    """Post command results immediately to API for faster feedback.

    This is best-effort - failures are logged but don't affect sensor operation.
    Heartbeat reporting serves as fallback if immediate POST fails.
    """
    try:
        # Read device token
        if not OXIMY_TOKEN_FILE.exists():
            logger.debug("No device token found - skipping immediate command result POST")
            return

        with open(OXIMY_TOKEN_FILE, encoding="utf-8") as f:
            device_token = f.read().strip()

        if not device_token:
            return

        # Prepare API request
        api_endpoint = os.getenv("OXIMY_API_ENDPOINT", "https://api.oximy.com/api/v1")
        url = f"{api_endpoint}/devices/command-results"

        headers = {
            "Authorization": f"Bearer {device_token}",
            "Content-Type": "application/json",
        }

        payload = json.dumps({"commandResults": command_results})

        # POST with short timeout (don't block sensor-config refresh)
        req = urllib.request.Request(url, data=payload.encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                logger.debug(f"Immediately posted command results: {list(command_results.keys())}")
            else:
                logger.debug(f"Immediate command POST returned status {response.status}")

    except Exception as e:
        # Silent failure - heartbeat will report results as fallback
        logger.debug(f"Failed to immediately POST command results (will retry via heartbeat): {e}")


def _parse_sensor_config(raw: dict, addon_instance=None) -> dict:
    """Parse API response into normalized config format.

    Also executes remote commands directly:
    - sensor_enabled: Enable/disable system proxy (with 6s debounce)
    - force_sync: Upload pending traces immediately
    - clear_cache: Delete local trace files
    - force_logout: Written to state file for Swift to handle (clears credentials)
    - appConfig: App-level feature flags for Swift to consume
    """
    global _command_results
    data = raw.get("data", raw)

    # Parse allowed_app_origins (hosts = browsers, non_hosts = AI-native apps)
    app_origins = data.get("allowed_app_origins", {})

    # Extract commands from API response
    commands = data.get("commands", {})

    # Extract appConfig from API response (app-level feature flags)
    app_config = data.get("appConfig", {})

    # --- EXECUTE COMMANDS DIRECTLY ---

    # Handle sensor_enabled with debounce (prevents rapid toggle from glitches)
    sensor_enabled = commands.get("sensor_enabled", True)
    current_time = time.time()

    with _state.lock:
        # First time initialization - apply immediately, no debounce
        if _state.previous_sensor_enabled is None:
            if not sensor_enabled:
                logger.info("Sensor disabled on startup - proxy not activated")
            try:
                _apply_sensor_state(sensor_enabled, addon_instance)
                _state.pending_state = None
                # Track execution result for heartbeat reporting
                _command_results["sensor_enabled"] = {
                    "success": True,
                    "executedAt": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                logger.warning(f"Failed to apply sensor state on startup: {e}")
                _command_results["sensor_enabled"] = {
                    "success": False,
                    "executedAt": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                }

        # State changed from current active state
        elif sensor_enabled != _state.previous_sensor_enabled:
            # Check if this is a new pending state or continuation
            if _state.pending_state != sensor_enabled:
                # New pending state, start debounce timer
                _state.pending_state = sensor_enabled
                _state.pending_since = current_time
                logger.info(f"Sensor state change pending: {_state.previous_sensor_enabled} -> {sensor_enabled} (debouncing for {SENSOR_DEBOUNCE_SECONDS}s)")
            elif current_time - _state.pending_since >= SENSOR_DEBOUNCE_SECONDS:
                # State has been stable for debounce period, apply it
                logger.info(f"Sensor state confirmed after {SENSOR_DEBOUNCE_SECONDS}s debounce")
                try:
                    _apply_sensor_state(sensor_enabled, addon_instance)
                    _state.pending_state = None
                    # Track execution result for heartbeat reporting
                    _command_results["sensor_enabled"] = {
                        "success": True,
                        "executedAt": datetime.now(timezone.utc).isoformat(),
                    }
                except Exception as e:
                    logger.warning(f"Failed to apply sensor state change: {e}")
                    _state.pending_state = None
                    _command_results["sensor_enabled"] = {
                        "success": False,
                        "executedAt": datetime.now(timezone.utc).isoformat(),
                        "error": str(e),
                    }
            else:
                # Still waiting for debounce
                remaining = SENSOR_DEBOUNCE_SECONDS - (current_time - _state.pending_since)
                logger.debug(f"Sensor state change pending, {remaining:.1f}s remaining")

        # State reverted to current before debounce completed
        elif _state.pending_state is not None:
            logger.info(f"Sensor state change cancelled (reverted to {sensor_enabled})")
            _state.pending_state = None
            # Track cancellation as a failed command execution
            _command_results["sensor_enabled"] = {
                "success": False,
                "executedAt": datetime.now(timezone.utc).isoformat(),
                "error": "State change cancelled - reverted before debounce completed",
            }

    # Handle force_sync (upload pending traces) - only execute if not already executed
    # This prevents re-execution on every config poll when using cached config
    force_sync = commands.get("force_sync", False)
    force_sync_hash = _get_command_hash("force_sync")
    if force_sync and force_sync_hash not in _executed_command_hashes:
        _executed_command_hashes.add(force_sync_hash)
        logger.info("Executing force_sync command (remote trigger)")
        start_time = time.time()
        success = False
        error_msg = None
        events_uploaded = 0
        bytes_uploaded = 0

        if addon_instance is not None:
            try:
                metrics = addon_instance.upload_all_traces()
                events_uploaded = metrics.get("eventsUploaded", 0)
                bytes_uploaded = metrics.get("bytesUploaded", 0)
                success = True
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"force_sync failed: {e}")
        else:
            error_msg = "No addon instance available"
            logger.debug("force_sync skipped: no addon instance available")

        duration = time.time() - start_time

        # Track execution result for heartbeat reporting with detailed metrics
        result_data = {
            "success": success,
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "eventsUploaded": events_uploaded,
            "bytesUploaded": bytes_uploaded,
            "duration": round(duration, 2),
        }
        if error_msg:
            result_data["error"] = error_msg

        _command_results["force_sync"] = result_data
    elif force_sync:
        logger.debug("force_sync already executed, skipping")

    # Handle clear_cache (delete local trace files) - only execute if not already executed
    clear_cache = commands.get("clear_cache", False)
    clear_cache_hash = _get_command_hash("clear_cache")
    if clear_cache and clear_cache_hash not in _executed_command_hashes:
        _executed_command_hashes.add(clear_cache_hash)
        logger.info("Executing clear_cache command")
        success = False
        error_msg = None
        try:
            _clear_local_cache()
            success = True
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"clear_cache failed: {e}")

        # Track execution result for heartbeat reporting
        _command_results["clear_cache"] = {
            "success": success,
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
        }
    elif clear_cache:
        logger.debug("clear_cache already executed, skipping")

    # Handle force_logout - execute whenever present
    force_logout = commands.get("force_logout", False)
    if force_logout:
        logger.info("Executing force_logout command (remote trigger)")
        # Track execution result for heartbeat reporting
        # Swift app handles the actual logout by monitoring remote-state.json
        _command_results["force_logout"] = {
            "success": True,
            "executedAt": datetime.now(timezone.utc).isoformat(),
        }

    # --- WRITE STATE FILE FOR SWIFT UI DISPLAY ---
    # Swift reads this for display purposes and handles force_logout + appConfig
    try:
        state_data = {
            "sensor_enabled": sensor_enabled,
            "force_logout": commands.get("force_logout", False),
            "tenantId": data.get("tenantId"),
            "itSupport": data.get("itSupport"),
            "proxy_active": _state.proxy_active,
            "proxy_port": _state.proxy_port,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "appConfig": app_config,
        }
        OXIMY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OXIMY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        logger.debug(f"Remote state written to {OXIMY_STATE_FILE}")
    except (IOError, OSError) as e:
        logger.warning(f"Failed to write remote state file: {e}")

    # --- WRITE COMMAND RESULTS FILE FOR HEARTBEAT REPORTING ---
    # Desktop apps read this file and include results in heartbeat payload
    if _command_results:
        try:
            OXIMY_COMMAND_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OXIMY_COMMAND_RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(_command_results, f, indent=2)
            logger.debug(f"Command results written to {OXIMY_COMMAND_RESULTS_FILE}: {list(_command_results.keys())}")

            # Immediately POST results to API for faster feedback (best effort)
            # Falls back to heartbeat reporting if this fails
            _post_command_results_immediate(_command_results)

            # Clear results after writing - they'll be sent in next heartbeat as fallback
            _command_results = {}
        except (IOError, OSError) as e:
            logger.warning(f"Failed to write command results file: {e}")

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


def load_output_config(config_path: Path | None = None) -> dict:
    """Load output configuration.

    Checks the following paths in order:
    1. Explicitly provided config_path
    2. Default path: ~/.oximy/config.json
    """
    default = {
        "output": {"directory": str(OXIMY_TRACES_DIR), "filename_pattern": "traces_{date}.jsonl"},
        "sensor_config_url": DEFAULT_SENSOR_CONFIG_URL,
        "sensor_config_cache": DEFAULT_SENSOR_CONFIG_CACHE,
        "config_refresh_interval_seconds": DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS,
    }

    # Determine which config file to load
    paths_to_check = []
    if config_path:
        paths_to_check.append(config_path)
    paths_to_check.append(OXIMY_CONFIG_FILE)

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
_device_id_lock = threading.Lock()


def get_device_id() -> str | None:
    """Get hardware UUID for this device. Cached after first call."""
    global _device_id_cache

    # Fast path: check cache without lock (safe for reads)
    if _device_id_cache is not None:
        return _device_id_cache

    # UUID validation pattern (8-4-4-4-12 hex format)
    UUID_PATTERN = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')

    def _is_valid_uuid(value: str) -> bool:
        return bool(UUID_PATTERN.match(value))

    with _device_id_lock:
        # Double-check after acquiring lock
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
                            # Use regex to extract UUID safely
                            uuid_match = re.search(r'"([a-fA-F0-9\-]{36})"', line)
                            if uuid_match:
                                candidate = uuid_match.group(1)
                                if _is_valid_uuid(candidate):
                                    _device_id_cache = candidate
                                    return _device_id_cache
                                else:
                                    logger.warning(f"Invalid UUID format from ioreg: {candidate}")
            elif sys.platform == "win32":
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    # Skip header and empty lines to find UUID
                    for line in lines:
                        candidate = line.strip()
                        # Skip empty lines and header
                        if not candidate or candidate.upper() == "UUID":
                            continue
                        if _is_valid_uuid(candidate):
                            _device_id_cache = candidate
                            return _device_id_cache
                        else:
                            logger.warning(f"Invalid UUID format from wmic: {candidate}")
                            break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"Failed to get device ID: {e}")

        return None


# =============================================================================
# MATCHING
# =============================================================================

# Cache for compiled URL pattern regexes (pattern -> compiled regex)
# Use OrderedDict for LRU eviction
from collections import OrderedDict
_url_pattern_cache: OrderedDict[str, re.Pattern] = OrderedDict()
_URL_PATTERN_CACHE_MAX_SIZE = 1000


def _build_url_regex(pattern: str) -> str:
    """Build regex string from glob-style URL pattern."""
    pattern_lower = pattern.lower()

    # Convert glob pattern to regex
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

    return f"^{regex}"


def _get_compiled_url_pattern(pattern: str) -> re.Pattern:
    """Get or create compiled regex for URL pattern. Uses LRU eviction."""
    if pattern in _url_pattern_cache:
        # Move to end (most recently used)
        _url_pattern_cache.move_to_end(pattern)
        return _url_pattern_cache[pattern]

    # Compile new pattern
    regex_str = _build_url_regex(pattern)
    compiled = re.compile(regex_str, re.IGNORECASE)

    # Evict oldest if cache is full
    if len(_url_pattern_cache) >= _URL_PATTERN_CACHE_MAX_SIZE:
        _url_pattern_cache.popitem(last=False)  # Remove oldest

    _url_pattern_cache[pattern] = compiled
    return compiled


def _extract_domain_from_pattern(pattern: str) -> str:
    """Extract just the domain portion from a URL pattern.

    Examples:
    - 'api.openai.com' -> 'api.openai.com'
    - 'api.openai.com/v1/chat' -> 'api.openai.com'
    - '*.openai.com/**/stream' -> '*.openai.com'
    - 'gemini.google.com/**/StreamGenerate*' -> 'gemini.google.com'
    """
    # Find first / which indicates start of path
    slash_idx = pattern.find('/')
    if slash_idx != -1:
        return pattern[:slash_idx]
    return pattern


def matches_domain(host: str, patterns: list[str]) -> str | None:
    """Check if host matches any pattern. Returns matched pattern or None.

    Handles both domain-only patterns and URL patterns with paths.
    For URL patterns, only the domain portion is matched.
    """
    host_lower = host.lower()

    for pattern in patterns:
        # Extract just the domain part (ignore path if present)
        domain_pattern = _extract_domain_from_pattern(pattern)
        pattern_lower = domain_pattern.lower()

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
        if "*" in pattern_lower and not pattern_lower.startswith("*"):
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

        # Match the remaining path pattern against URL path using cached regex
        compiled = _get_compiled_url_pattern(path_pattern)
        return bool(compiled.match(url_path))

    # Use cached compiled regex for the full pattern
    compiled = _get_compiled_url_pattern(pattern_lower)
    return bool(compiled.match(url_lower))


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
    """Check if text contains any blacklisted word. Returns the word or None.

    Note: words list should be pre-lowercased for optimal performance.
    """
    if not text:
        return None
    text_lower = text.lower()
    for word in words:
        # Words are expected to be pre-lowercased when config is loaded
        if word in text_lower:
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

    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.debug(f"Could not parse GraphQL operation name: {e}")

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

    # Windows browser detection - uses module-level WINDOWS_BROWSERS constant
    if bundle_lower in WINDOWS_BROWSERS:
        return "host"

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


class TLSPassthrough:
    """Manages TLS passthrough for certificate-pinned hosts."""

    _CACHE_MAX_SIZE = 1000  # LRU cache limit

    def __init__(self, patterns: list[str]):
        """Initialize with patterns from API config."""
        self._patterns: list[re.Pattern] = []
        self._learned_patterns: list[str] = []
        self._result_cache: OrderedDict[str, bool] = OrderedDict()  # LRU cache

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
        if OXIMY_PASSTHROUGH_CACHE.exists():
            try:
                with open(OXIMY_PASSTHROUGH_CACHE, encoding="utf-8") as f:
                    data = json.load(f)
                self._learned_patterns = data.get("patterns", [])
                for p in self._learned_patterns:
                    try:
                        self._patterns.append(re.compile(p, re.IGNORECASE))
                    except re.error as e:
                        logger.debug(f"Invalid learned passthrough pattern '{p}': {e}")
                if self._learned_patterns:
                    logger.info(f"Loaded {len(self._learned_patterns)} learned passthrough patterns")
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Could not load learned passthrough cache: {e}")

    def should_passthrough(self, host: str) -> bool:
        """Check if host should bypass TLS interception."""
        # Check cache first (LRU)
        if host in self._result_cache:
            self._result_cache.move_to_end(host)  # Mark as recently used
            return self._result_cache[host]

        result = any(p.match(host) for p in self._patterns)

        # Cache the result with LRU eviction
        if len(self._result_cache) >= self._CACHE_MAX_SIZE:
            self._result_cache.popitem(last=False)  # Remove oldest
        self._result_cache[host] = result

        return result

    def add_host(self, host: str) -> None:
        """Add a learned host to local passthrough cache."""
        try:
            pattern = f"^{re.escape(host)}$"
            if pattern in self._learned_patterns:
                return

            self._learned_patterns.append(pattern)
            self._patterns.append(re.compile(pattern, re.IGNORECASE))

            # Clear result cache since patterns changed
            self._result_cache.clear()

            # Save to local cache
            OXIMY_PASSTHROUGH_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(OXIMY_PASSTHROUGH_CACHE, "w", encoding="utf-8") as f:
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

        # Add cert-pinned hosts to passthrough so future connections bypass TLS interception
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
            except re.error as e:
                logger.debug(f"Invalid learned passthrough pattern '{p}': {e}")
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
# MEMORY BUFFER FOR CLOUD-FIRST INGESTION
# =============================================================================

def _get_dynamic_buffer_size() -> int:
    """Calculate buffer size as 1% of system RAM, capped 20-200 MB."""
    MIN_BYTES = 20 * 1024 * 1024   # 20 MB floor
    MAX_BYTES = 200 * 1024 * 1024  # 200 MB ceiling

    # Check for override via environment variable
    override = os.environ.get("OXIMY_BUFFER_MAX_MB")
    if override:
        try:
            return int(override) * 1024 * 1024
        except ValueError:
            logger.warning(f"Invalid OXIMY_BUFFER_MAX_MB value '{override}', using auto-detection")

    # Get total system memory (cross-platform)
    try:
        # Linux/macOS
        total_ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError):
        try:
            # Windows fallback
            import psutil
            total_ram = psutil.virtual_memory().total
        except ImportError:
            logger.warning("Could not detect system memory, using conservative 2GB assumption")
            total_ram = 2 * 1024 * 1024 * 1024  # Conservative 2 GB fallback

    # 1% of total RAM, capped
    target = total_ram // 100
    return max(MIN_BYTES, min(target, MAX_BYTES))


BUFFER_MAX_BYTES = _get_dynamic_buffer_size()
BUFFER_MAX_COUNT = 100  # Hard cap on trace count (safety valve)


class MemoryTraceBuffer:
    """Thread-safe in-memory buffer with byte-based limit for cloud-first ingestion."""

    def __init__(self, max_bytes: int = BUFFER_MAX_BYTES, max_count: int = BUFFER_MAX_COUNT):
        self._buffer: list[tuple[dict, int]] = []  # (event, serialized_size)
        self._lock = threading.Lock()
        self._max_bytes = max_bytes
        self._max_count = max_count
        self._current_bytes = 0
        logger.info(f"Memory buffer initialized: max {max_bytes // (1024 * 1024)} MB, {max_count} traces")

    def append(self, event: dict) -> bool:
        """Add event to buffer. Returns False if buffer is full."""
        # Calculate serialized size (what we'd send over network)
        serialized = json.dumps(event, separators=(",", ":")).encode("utf-8")
        size = len(serialized)

        with self._lock:
            # Check both limits
            if self._current_bytes + size > self._max_bytes:
                return False
            if len(self._buffer) >= self._max_count:
                return False

            self._buffer.append((event, size))
            self._current_bytes += size
            return True

    def take_batch(self, max_bytes: int = 5 * 1024 * 1024) -> list[dict]:
        """Remove and return events up to max_bytes (default 5MB per batch)."""
        with self._lock:
            batch = []
            batch_bytes = 0
            while self._buffer and batch_bytes < max_bytes:
                event, size = self._buffer[0]
                if batch_bytes + size > max_bytes and batch:
                    break  # Would exceed limit and we have something
                self._buffer.pop(0)
                self._current_bytes -= size
                batch.append(event)
                batch_bytes += size
            return batch

    def prepend_batch(self, events: list[dict]) -> None:
        """Add events back to front of buffer (for retry after failed upload)."""
        with self._lock:
            for event in reversed(events):
                serialized = json.dumps(event, separators=(",", ":")).encode("utf-8")
                size = len(serialized)
                self._buffer.insert(0, (event, size))
                self._current_bytes += size

    def peek_all(self) -> list[dict]:
        """Return copy of all events without removing."""
        with self._lock:
            return [event for event, _ in self._buffer]

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def bytes_used(self) -> int:
        with self._lock:
            return self._current_bytes

    @property
    def max_bytes(self) -> int:
        """Return the maximum buffer capacity in bytes."""
        return self._max_bytes

    def clear(self):
        with self._lock:
            self._buffer.clear()
            self._current_bytes = 0


# =============================================================================
# DIRECT TRACE UPLOADER (Memory to API)
# =============================================================================

# Ingest API URL - configurable via environment variable for testing/staging
DEFAULT_INGEST_API_URL = "https://api.oximy.com/api/v1/ingest/network-traces"
INGEST_API_URL = os.environ.get("OXIMY_INGEST_URL", DEFAULT_INGEST_API_URL)


def _log_api_call(
    url: str,
    method: str,
    headers: dict,
    body_bytes: bytes,
    response_code: int | None,
    response_body: str | None,
    error: str | None = None,
) -> None:
    """Log an API call as a curl command with its response to terminal (verbose)."""
    # Build curl command (body is gzipped, so we note that)
    header_args = " ".join(f"-H '{k}: {v}'" for k, v in headers.items() if k != "Authorization")
    auth_header = "-H 'Authorization: Bearer <TOKEN>'" if "Authorization" in headers else ""

    curl_cmd = (
        f"curl -s -X {method} {header_args} {auth_header} "
        f"--data-binary '<gzip: {len(body_bytes)}B>' '{url}'"
    )

    if error:
        logger.info(f"[API] {curl_cmd}")
        logger.info(f"[API] ERROR: {error}")
    else:
        logger.info(f"[API] {curl_cmd}")
        logger.info(f"[API] Response {response_code}: {response_body}")


def _get_device_token() -> str | None:
    """Read device token from file (written by Swift/host app)."""
    try:
        if OXIMY_TOKEN_FILE.exists():
            token = OXIMY_TOKEN_FILE.read_text().strip()
            if token:
                return token
    except (IOError, OSError) as e:
        logger.debug(f"Could not read device token: {e}")
    return None


class DirectTraceUploader:
    """Uploads traces directly from memory buffer to API with retry logic."""

    BATCH_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per upload batch
    MAX_RETRIES = 3
    # Support env var override: OXIMY_UPLOAD_RETRY_DELAYS="0.5,1.0,2.0"
    _retry_delays_str = os.environ.get("OXIMY_UPLOAD_RETRY_DELAYS", "0.5,1.0,2.0")
    try:
        RETRY_DELAYS = [float(x) for x in _retry_delays_str.split(",")]
    except ValueError:
        RETRY_DELAYS = [0.5, 1.0, 2.0]  # Fallback to defaults

    def __init__(self, buffer: MemoryTraceBuffer, api_url: str = INGEST_API_URL):
        self._buffer = buffer
        self._api_url = api_url

    def upload_batch(self) -> bool:
        """Upload one batch from buffer. Returns True if successful or empty."""
        batch = self._buffer.take_batch(self.BATCH_MAX_BYTES)
        if not batch:
            return True  # Nothing to upload

        for attempt in range(self.MAX_RETRIES):
            try:
                payload = "\n".join(
                    json.dumps(e, separators=(",", ":")) for e in batch
                )
                compressed = gzip.compress(payload.encode("utf-8"))

                headers = {
                    "Content-Type": "application/jsonl",
                    "Content-Encoding": "gzip",
                    "User-Agent": "Oximy-Sensor/1.0",
                }
                # Add device token for authentication
                token = _get_device_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"

                req = urllib.request.Request(
                    self._api_url,
                    data=compressed,
                    headers=headers,
                    method="POST",
                )

                with _no_proxy_opener.open(req, timeout=30) as resp:
                    response_body = resp.read().decode("utf-8")
                    response_data = json.loads(response_body)
                    # Log successful API call
                    _log_api_call(
                        url=self._api_url,
                        method="POST",
                        headers=headers,
                        body_bytes=compressed,
                        response_code=resp.status,
                        response_body=response_body,
                    )
                    if response_data.get("success"):
                        logger.info(f"Uploaded {len(batch)} traces ({len(compressed)} bytes compressed)")
                        return True
                    else:
                        logger.warning(f"Upload rejected: {response_data.get('error', 'Unknown error')}")

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                # Log failed API call
                _log_api_call(
                    url=self._api_url,
                    method="POST",
                    headers=headers,
                    body_bytes=compressed,
                    response_code=e.code,
                    response_body=error_body,
                    error=f"HTTPError {e.code}",
                )
                if e.code == 401:
                    logger.warning(f"Upload auth failed (401): device token missing or invalid. Check ~/.oximy/device-token")
                else:
                    logger.debug(f"Upload attempt {attempt + 1} HTTP error {e.code}: {error_body[:200]}")
            except (urllib.error.URLError, OSError) as e:
                # Log network error
                _log_api_call(
                    url=self._api_url,
                    method="POST",
                    headers=headers,
                    body_bytes=compressed,
                    response_code=None,
                    response_body=None,
                    error=str(e),
                )
                logger.debug(f"Upload attempt {attempt + 1} failed: {e}")

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAYS[attempt])

        # All retries failed - put batch back at front of buffer
        logger.warning(f"Upload failed after {self.MAX_RETRIES} attempts, returning {len(batch)} traces to buffer")
        self._buffer.prepend_batch(batch)
        return False

    def upload_all(self) -> int:
        """Upload all buffered traces. Returns count of traces uploaded."""
        total_uploaded = 0
        while self._buffer.size() > 0:
            size_before = self._buffer.size()
            if not self.upload_batch():
                return total_uploaded  # Return partial count on failure
            total_uploaded += size_before - self._buffer.size()
        return total_uploaded


# =============================================================================
# TRACE UPLOADER (Disk-based fallback)
# =============================================================================

# Number of traces per upload batch (for disk-based uploads)
# Chosen for balance between API call overhead and memory usage
BATCH_SIZE = 500
# Upload interval/threshold are now configurable via config.json (upload.interval_seconds, upload.threshold_count)
DEFAULT_UPLOAD_INTERVAL_SECONDS = 3.0  # Default: upload every N seconds
DEFAULT_UPLOAD_THRESHOLD_COUNT = 100  # Default: or every N traces


class TraceUploader:
    """Uploads traces to the ingestion API with gzip compression."""

    def __init__(self):
        self._upload_state: dict[str, int] = {}  # file_path -> last_uploaded_line
        self._load_state()

    def _load_state(self) -> None:
        """Load upload state from disk."""
        if OXIMY_UPLOAD_STATE_FILE.exists():
            try:
                with open(OXIMY_UPLOAD_STATE_FILE, encoding="utf-8") as f:
                    self._upload_state = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Could not load upload state: {e}")

    def _save_state(self) -> None:
        """Save upload state to disk."""
        try:
            OXIMY_UPLOAD_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OXIMY_UPLOAD_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._upload_state, f)
        except IOError as e:
            logger.warning(f"Failed to save upload state: {e}")

    def upload_traces(self, trace_file: Path) -> tuple[int, bool]:
        """Upload pending traces from a file.

        Returns:
            tuple[int, bool]: (traces_uploaded, is_fully_uploaded)
                - traces_uploaded: number of traces successfully uploaded
                - is_fully_uploaded: True if all lines in file have been uploaded
        """
        import gzip

        if not trace_file.exists():
            return 0, False

        file_key = str(trace_file)
        last_uploaded = self._upload_state.get(file_key, 0)

        # Read all lines from the file
        try:
            with open(trace_file, encoding="utf-8") as f:
                lines = f.readlines()
        except IOError as e:
            logger.warning(f"Failed to read trace file: {e}")
            return 0, False

        total_lines = len(lines)

        # Handle file truncation/recreation: if file has fewer lines than recorded,
        # reset state and upload from the beginning
        if total_lines < last_uploaded:
            logger.info(f"Trace file was truncated/recreated (had {last_uploaded}, now {total_lines}), resetting upload state")
            last_uploaded = 0
            self._upload_state[file_key] = 0
            self._save_state()

        # Get pending lines (not yet uploaded)
        pending_lines = lines[last_uploaded:]
        if not pending_lines:
            # No pending lines - file is fully uploaded
            is_fully_uploaded = total_lines > 0 and last_uploaded >= total_lines
            return 0, is_fully_uploaded

        total_uploaded = 0

        # Upload in batches
        for i in range(0, len(pending_lines), BATCH_SIZE):
            batch = pending_lines[i:i + BATCH_SIZE]
            batch_data = "".join(batch).encode("utf-8")

            # Gzip compress the batch
            compressed = gzip.compress(batch_data)

            try:
                headers = {
                    "Content-Type": "application/jsonl",
                    "Content-Encoding": "gzip",
                    "User-Agent": "Oximy-Sensor/1.0",
                }
                # Add device token for authentication
                token = _get_device_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"

                req = urllib.request.Request(
                    INGEST_API_URL,
                    data=compressed,
                    headers=headers,
                    method="POST",
                )

                with _no_proxy_opener.open(req, timeout=30) as resp:
                    response_body = resp.read().decode("utf-8")
                    response_data = json.loads(response_body)
                    # Log successful API call
                    _log_api_call(
                        url=INGEST_API_URL,
                        method="POST",
                        headers=headers,
                        body_bytes=compressed,
                        response_code=resp.status,
                        response_body=response_body,
                    )

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
                # Log failed API call
                _log_api_call(
                    url=INGEST_API_URL,
                    method="POST",
                    headers=headers,
                    body_bytes=compressed,
                    response_code=e.code,
                    response_body=error_body,
                    error=f"HTTPError {e.code}",
                )
                if e.code == 401:
                    logger.warning(f"Upload auth failed (401): device token missing or invalid. Check ~/.oximy/device-token")
                else:
                    logger.warning(f"Upload HTTP error {e.code}: {error_body[:200]}")
                break
            except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
                # Log network error
                _log_api_call(
                    url=INGEST_API_URL,
                    method="POST",
                    headers=headers,
                    body_bytes=compressed,
                    response_code=None,
                    response_body=None,
                    error=str(e),
                )
                logger.warning(f"Upload failed: {e}")
                break

        # Check if fully uploaded after this batch
        is_fully_uploaded = total_lines > 0 and last_uploaded >= total_lines
        return total_uploaded, is_fully_uploaded

    def upload_all_pending(self, traces_dir: Path, active_file: Path | None = None) -> int:
        """Upload all pending traces from all files in the directory.

        Args:
            traces_dir: Directory containing trace files
            active_file: Currently active trace file being written to (don't delete)

        Returns:
            Total number of traces uploaded
        """
        if not traces_dir.exists():
            return 0

        # Normalize active_file path for reliable comparison
        active_file_resolved = active_file.resolve() if active_file else None

        total = 0
        for trace_file in sorted(traces_dir.glob("traces_*.jsonl")):
            uploaded, is_fully_uploaded = self.upload_traces(trace_file)
            total += uploaded

            # Delete fully-uploaded files (but not the active file being written to)
            # Use resolved paths for reliable comparison across different path representations
            is_active = active_file_resolved and trace_file.resolve() == active_file_resolved
            if is_fully_uploaded and not is_active:
                try:
                    trace_file.unlink()
                    logger.info(f"Cleaned up fully-uploaded trace file: {trace_file.name}")
                    # Remove from upload state since file no longer exists
                    file_key = str(trace_file)
                    if file_key in self._upload_state:
                        del self._upload_state[file_key]
                        self._save_state()
                except OSError as e:
                    logger.warning(f"Failed to delete trace file {trace_file}: {e}")

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
        # Cloud-first ingestion: memory buffer with disk fallback
        self._buffer: MemoryTraceBuffer | None = None
        self._direct_uploader: DirectTraceUploader | None = None
        # Disk-based fallback (lazy-initialized only when needed)
        self._writer: TraceWriter | None = None
        self._debug_writer: TraceWriter | None = None  # Unfiltered logs
        self._uploader: TraceUploader | None = None  # For uploading fallback JSONL files
        self._resolver: ProcessResolver | None = None
        self._client_processes: dict[str, ClientProcess] = {}  # client_conn.id -> ClientProcess
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
        self._thread_start_lock: threading.Lock = threading.Lock()  # Protects thread startup
        self._force_sync_thread: threading.Thread | None = None
        self._force_sync_stop: threading.Event = threading.Event()
        self._debug_ingestion: bool = False  # Debug mode: write to disk AND memory buffer
        # Configurable upload settings (read from config.json)
        self._upload_interval_seconds: float = DEFAULT_UPLOAD_INTERVAL_SECONDS
        self._upload_threshold_count: int = DEFAULT_UPLOAD_THRESHOLD_COUNT
        self._port_configured: bool = False  # Guard against configure() recursion when setting listen_port

    def _get_config_snapshot(self) -> dict:
        """Get a consistent snapshot of all filtering config.

        PERFORMANCE: Returns cached tuple references instead of copying lists
        on every request. Config only changes every 30 minutes during refresh.
        The tuples are immutable so safe to share across requests.
        """
        # Fast path: return cached snapshot without lock
        # Lists are converted to tuples during _refresh_config and _apply_config
        # so they're safe to return directly
        return {
            "whitelist": self._whitelist,
            "blacklist": self._blacklist,
            "allowed_app_hosts": self._allowed_app_hosts,
            "allowed_app_non_hosts": self._allowed_app_non_hosts,
            "allowed_host_origins": self._allowed_host_origins,
        }

    def _ensure_writer(self) -> TraceWriter | None:
        """Lazily initialize disk-based trace writer for debug ingestion or emergency fallback."""
        logger.debug(f"_ensure_writer: _writer is None={self._writer is None}, _output_dir={self._output_dir}")
        if self._writer is None and self._output_dir:
            self._writer = TraceWriter(self._output_dir, self._filename_pattern)
            logger.info(f"Disk writer initialized: {self._output_dir}")
        return self._writer

    def _write_to_buffer(self, event: dict) -> bool:
        """Write event to memory buffer. Falls back to disk if buffer full.

        In debug ingestion mode, also writes to disk for inspection.
        Returns True if written successfully (to buffer or disk), False otherwise.
        """
        if self._buffer is None:
            return False

        # Debug mode: also write to disk for inspection
        if self._debug_ingestion:
            logger.debug(f"_write_to_buffer: debug_ingestion=True, calling _ensure_writer")
            writer = self._ensure_writer()
            if writer:
                writer.write(event)
            else:
                logger.warning("_write_to_buffer: _ensure_writer returned None!")

        # Add to memory buffer for cloud upload
        if self._buffer.append(event):
            self._traces_since_upload += 1
            return True

        # Buffer full - emergency fallback to disk (only if not already written in debug mode)
        if not self._debug_ingestion:
            logger.warning(f"Memory buffer full ({self._buffer.bytes_used()} bytes), writing to disk")
            writer = self._ensure_writer()
            if writer:
                writer.write(event)
        return True

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option("oximy_enabled", bool, False, "Enable AI traffic capture")
        loader.add_option("oximy_config", str, "", "Path to config.json")
        loader.add_option("oximy_output_dir", str, "~/.oximy/traces", "Output directory")
        loader.add_option("oximy_verbose", bool, False, "Verbose logging")
        loader.add_option("oximy_upload_enabled", bool, True, "Enable trace uploads (disable if host app handles sync)")
        loader.add_option("oximy_debug_traces", bool, False, "Log all requests to all_traces file (unfiltered)")
        loader.add_option("oximy_debug_ingestion", bool, False, "Write traces to disk AND send via memory buffer (for debugging)")
        loader.add_option("oximy_manage_proxy", bool, True, "Manage system proxy (disable when host app handles this)")

    def _refresh_config(self, max_retries: int = 3) -> bool:
        """Fetch and apply updated config from API with retries.

        Returns True if config was successfully refreshed, False otherwise.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # fetch_sensor_config returns already-parsed config and executes commands
                config = fetch_sensor_config(
                    self._sensor_config_url,
                    self._sensor_config_cache,
                    addon_instance=self
                )

                # Atomic update with lock to ensure consistent state
                # Use tuples for immutability - safe to share across requests without copying
                with self._config_lock:
                    self._whitelist = tuple(config.get("whitelist", []))
                    # Pre-lowercase blacklist words for faster matching
                    self._blacklist = tuple(w.lower() for w in config.get("blacklist", []))

                    # Update hierarchical filtering config
                    app_origins = config.get("allowed_app_origins", {})
                    self._allowed_app_hosts = tuple(app_origins.get("hosts", []))
                    self._allowed_app_non_hosts = tuple(app_origins.get("non_hosts", []))
                    self._allowed_host_origins = tuple(config.get("allowed_host_origins", []))

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
                if OXIMY_FORCE_SYNC_TRIGGER.exists():
                    logger.info("Force sync trigger detected")
                    try:
                        OXIMY_FORCE_SYNC_TRIGGER.unlink()  # Delete trigger file
                    except OSError as e:
                        logger.debug(f"Could not delete force sync trigger: {e}")

                    # Cloud-first: upload from memory buffer first
                    buffer_uploaded = 0
                    if self._direct_uploader and self._buffer and self._buffer.size() > 0:
                        try:
                            buffer_uploaded = self._direct_uploader.upload_all()
                            if buffer_uploaded > 0:
                                logger.info(f"Force sync: uploaded {buffer_uploaded} traces from memory buffer")
                        except Exception as e:
                            logger.warning(f"Force sync from buffer failed: {e}")

                    # Then upload any disk fallback files
                    if self._uploader and self._output_dir:
                        try:
                            if self._writer and self._writer._fo:
                                self._writer._fo.flush()
                            # Pass active file to avoid deleting file currently being written
                            active_file = self._writer._current_file if self._writer else None
                            uploaded = self._uploader.upload_all_pending(self._output_dir, active_file=active_file)
                            if uploaded > 0:
                                logger.info(f"Force sync: uploaded {uploaded} traces from disk fallback")
                            elif buffer_uploaded == 0:
                                logger.info("Force sync: no pending traces to upload")
                        except Exception as e:
                            logger.warning(f"Force sync from disk failed: {e}")

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
        log_level = logging.DEBUG if ctx.options.oximy_verbose else logging.INFO
        logger.setLevel(log_level)
        # Also set process module logger to same level for debugging
        logging.getLogger("mitmproxy.addons.oximy.process").setLevel(log_level)

        # Register cleanup handlers for graceful shutdown
        _register_cleanup_handlers()

        # Check certificate before anything else (macOS only)
        if sys.platform == "darwin":
            if not _ensure_cert_trusted():
                # Use warning (not error) to avoid triggering mitmproxy's errorcheck addon
                # which exits the process on startup errors. The proxy can still run;
                # HTTPS interception just won't work until cert is installed via MDM.
                logger.warning("=" * 60)
                logger.warning("CERTIFICATE NOT TRUSTED - HTTPS interception will fail!")
                logger.warning("To install manually, run:")
                logger.warning(f"  sudo security add-trusted-cert -d -r trustRoot -p ssl -k /Library/Keychains/System.keychain {_get_cert_path()}")
                logger.warning("=" * 60)
                # Continue anyway - user might install manually or cert will be generated
            else:
                logger.info("***** OXIMY CERTIFICATE TRUSTED ****")

        # Load local config (output settings, refresh interval, etc.)
        output_config = load_output_config(Path(ctx.options.oximy_config) if ctx.options.oximy_config else None)
        self._output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._filename_pattern = output_config["output"].get("filename_pattern", "traces_{date}.jsonl")
        logger.info(f"Output dir: {self._output_dir}, Pattern: {self._filename_pattern}")

        # Cloud-first ingestion: initialize memory buffer and direct uploader
        self._buffer = MemoryTraceBuffer()
        upload_config = output_config.get("upload", {})
        ingest_url = upload_config.get("ingest_api_url", INGEST_API_URL)
        self._direct_uploader = DirectTraceUploader(self._buffer, ingest_url)
        # Configurable upload interval and threshold (for scalability: 3s now, 30s later)
        # Validate with sane bounds: interval 0.5-300s, threshold 1-10000 traces
        try:
            interval = float(upload_config.get("interval_seconds", DEFAULT_UPLOAD_INTERVAL_SECONDS))
            self._upload_interval_seconds = max(0.5, min(interval, 300.0))
            if interval != self._upload_interval_seconds:
                logger.warning(f"Upload interval {interval}s clamped to {self._upload_interval_seconds}s (valid range: 0.5-300s)")
        except (ValueError, TypeError):
            logger.warning(f"Invalid upload interval in config, using default {DEFAULT_UPLOAD_INTERVAL_SECONDS}s")
            self._upload_interval_seconds = DEFAULT_UPLOAD_INTERVAL_SECONDS

        try:
            threshold = int(upload_config.get("threshold_count", DEFAULT_UPLOAD_THRESHOLD_COUNT))
            self._upload_threshold_count = max(1, min(threshold, 10000))
            if threshold != self._upload_threshold_count:
                logger.warning(f"Upload threshold {threshold} clamped to {self._upload_threshold_count} (valid range: 1-10000)")
        except (ValueError, TypeError):
            logger.warning(f"Invalid upload threshold in config, using default {DEFAULT_UPLOAD_THRESHOLD_COUNT}")
            self._upload_threshold_count = DEFAULT_UPLOAD_THRESHOLD_COUNT

        logger.info(f"Ingestion API: {ingest_url} (upload every {self._upload_interval_seconds}s or {self._upload_threshold_count} traces)")
        # Disk-based writer is lazy-initialized only when needed (emergency fallback)
        self._writer = None

        # Debug traces (unfiltered) - only if enabled
        if ctx.options.oximy_debug_traces:
            self._debug_writer = TraceWriter(self._output_dir, "all_traces_{date}.jsonl")
            logger.info("Debug traces enabled: logging all requests to all_traces_{date}.jsonl")
        else:
            self._debug_writer = None

        # Debug ingestion mode: write to disk AND send via memory buffer
        self._debug_ingestion = ctx.options.oximy_debug_ingestion
        if self._debug_ingestion:
            logger.info("Debug ingestion mode: writing traces to disk AND memory buffer")

        self._sensor_config_url = output_config.get("sensor_config_url", DEFAULT_SENSOR_CONFIG_URL)
        self._sensor_config_cache = output_config.get("sensor_config_cache", DEFAULT_SENSOR_CONFIG_CACHE)
        self._config_refresh_interval = output_config.get("config_refresh_interval_seconds", DEFAULT_CONFIG_REFRESH_INTERVAL_SECONDS)
        # Ensure output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Fetch sensor config from API (cached locally)
        # Use tuples for immutability - safe to share across requests without copying
        # Pass self for command execution (sensor_enabled, force_sync, clear_cache)
        sensor_config = fetch_sensor_config(
            self._sensor_config_url,
            self._sensor_config_cache,
            addon_instance=self
        )
        self._whitelist = tuple(sensor_config.get("whitelist", []))
        # Pre-lowercase blacklist words for faster matching
        self._blacklist = tuple(w.lower() for w in sensor_config.get("blacklist", []))
        passthrough_patterns = sensor_config.get("passthrough", [])
        self._tls = TLSPassthrough(passthrough_patterns)

        # Hierarchical filtering config
        app_origins = sensor_config.get("allowed_app_origins", {})
        self._allowed_app_hosts = tuple(app_origins.get("hosts", []))
        self._allowed_app_non_hosts = tuple(app_origins.get("non_hosts", []))
        self._allowed_host_origins = tuple(sensor_config.get("allowed_host_origins", []))

        # Start periodic config refresh (only if not already running) - thread-safe
        if self._config_refresh_thread is None or not self._config_refresh_thread.is_alive():
            with self._thread_start_lock:
                # Double-check after acquiring lock
                if self._config_refresh_thread is None or not self._config_refresh_thread.is_alive():
                    self._start_config_refresh_task()

        # Start background trigger file monitor
        self._start_force_sync_monitor()

        # Initialize trace uploader for disk-based fallback files (only if enabled)
        # When running under a host app (e.g., OximyMac), the host handles sync
        if ctx.options.oximy_upload_enabled:
            self._uploader = TraceUploader()
            self._last_upload_time = time.time()
            self._traces_since_upload = 0
            logger.info("Cloud-first trace upload enabled")

            # Check for existing JSONL files from previous emergency disk writes
            # and upload them to clear the backlog (delete files after successful upload)
            if self._output_dir and self._output_dir.exists():
                try:
                    # At startup, no active writer yet, so all files can be deleted if fully uploaded
                    uploaded = self._uploader.upload_all_pending(self._output_dir, active_file=None)
                    if uploaded > 0:
                        logger.info(f"Uploaded {uploaded} traces from previous emergency disk writes")
                except Exception as e:
                    logger.warning(f"Failed to upload existing disk traces on startup: {e}")
        else:
            self._uploader = None
            logger.info("Trace upload disabled (host app handles sync)")

        # Initialize process resolver for client attribution
        # Pass proxy port so resolver can query active connections efficiently
        proxy_port = ctx.options.listen_port or 8080
        self._resolver = ProcessResolver(proxy_port=proxy_port)

        # Get device ID
        self._device_id = get_device_id()
        logger.info(f"Device ID: {self._device_id}")

        logger.info(
            f"===== OXIMY READY: {len(self._whitelist)} whitelist, {len(self._blacklist)} blacklist, "
            f"{len(passthrough_patterns)} passthrough, {len(self._allowed_app_hosts)} app_hosts, "
            f"{len(self._allowed_host_origins)} host_origins ====="
        )

        # Start delayed proxy activation fallback (workaround for unreliable running() callback)
        threading.Timer(5.0, self._delayed_proxy_activation).start()
        logger.info("[OXIMY] Scheduled delayed proxy activation fallback in 5s")

    def running(self) -> None:
        """Called after mitmproxy is fully started and listening."""
        logger.info("[OXIMY] running() callback triggered")

        if not self._enabled:
            logger.info("[OXIMY] Addon disabled, skipping proxy setup in running()")
            return

        if not ctx.options.oximy_manage_proxy:
            logger.info("[OXIMY] Proxy management disabled, skipping proxy setup in running()")
            return

        if self._port_configured:
            logger.info("[OXIMY] Proxy already configured (likely by fallback), skipping running()")
            return

        global _addon_manages_proxy
        self._port_configured = True

        # Get actual bound port from proxyserver (available now that server is running)
        proxyserver = ctx.master.addons.get("proxyserver")
        if proxyserver and proxyserver.listen_addrs():
            with _state.lock:
                _state.proxy_port = str(proxyserver.listen_addrs()[0][1])
                # Write port file so terminal env script can discover the port
                _write_proxy_port_file(_state.proxy_port)
                # Only enable proxy if sensor is active (may be disabled on startup)
                if _state.sensor_active:
                    logger.info(f"Configuring system proxy with port {_state.proxy_port}")
                    _set_system_proxy(enable=True)
                    _addon_manages_proxy = True
                    _state.proxy_active = True
                    _write_proxy_state()
                else:
                    logger.info(f"Proxy port {_state.proxy_port} captured, but sensor disabled - proxy not activated")
                    _addon_manages_proxy = False
                    _state.proxy_active = False
                    _write_proxy_state()
        else:
            logger.warning("Could not get proxy port - system proxy not configured")

        # Set up terminal env (shell profile injection, env scripts, CA bundle).
        # Runs outside the lock — idempotent and non-fatal.
        _setup_terminal_env()

    def _delayed_proxy_activation(self):
        """Fallback activation if running() hook isn't called.

        This is a workaround for mitmproxy's unreliable lifecycle hooks.
        If running() executes first, it will set proxy_active and this will be a no-op.
        """
        try:
            if self._port_configured:
                logger.info("[OXIMY] Fallback: Proxy already configured by running(), skipping")
                return

            if not self._enabled:
                logger.info("[OXIMY] Fallback: Addon disabled, skipping")
                return

            if not ctx.options.oximy_manage_proxy:
                logger.info("[OXIMY] Fallback: Proxy management disabled, skipping")
                return

            # Get the actual bound port from proxyserver
            proxyserver = ctx.master.addons.get("proxyserver")
            if not proxyserver:
                logger.warning("[OXIMY] Fallback: proxyserver addon not found")
                return

            listen_addrs = proxyserver.listen_addrs()
            if not listen_addrs:
                logger.warning("[OXIMY] Fallback: No listen addresses found")
                return

            port = listen_addrs[0][1]
            logger.info(f"[OXIMY] Fallback: Detected proxy listening on port {port}")

            # Mark as configured to prevent running() from also doing this
            global _addon_manages_proxy
            self._port_configured = True

            # Set proxy active
            with _state.lock:
                _state.proxy_port = str(port)
                _write_proxy_port_file(_state.proxy_port)

                # Only enable proxy if sensor is active
                if _state.sensor_active:
                    logger.info(f"[OXIMY] Fallback: Configuring system proxy with port {_state.proxy_port}")
                    _set_system_proxy(enable=True)
                    _addon_manages_proxy = True
                    _state.proxy_active = True
                    _write_proxy_state()
                    logger.info(f"[OXIMY] Fallback: Proxy marked as active on port {port}")
                else:
                    logger.info(f"[OXIMY] Fallback: Proxy port {_state.proxy_port} captured, but sensor disabled")
                    _addon_manages_proxy = False
                    _state.proxy_active = False
                    _write_proxy_state()

            # Set up terminal env
            _setup_terminal_env()

        except Exception as e:
            logger.error(f"[OXIMY] Fallback activation failed: {e}", exc_info=True)

    async def client_connected(self, client: connection.Client) -> None:
        """Resolve client process at connection time when TCP is definitely active.

        This is more reliable than resolving during request() because the TCP
        connection is guaranteed to be active at this point. For HTTP/2 and
        keep-alive connections, this amortizes the cost across many requests.
        """
        if not self._enabled or not self._resolver:
            return

        try:
            client_port = client.peername[1]
            client_process = await self._resolver.get_process_for_port(client_port)
            self._client_processes[client.id] = client_process
            logger.debug(f"[CLIENT_CONNECTED] port={client_port} -> {client_process.name} (bundle: {client_process.bundle_id})")
        except Exception as e:
            logger.debug(f"[CLIENT_CONNECTED] Failed to resolve process for port {client.peername[1] if client.peername else 'unknown'}: {e}")

    def client_disconnected(self, client: connection.Client) -> None:
        """Clean up client process mapping when connection closes."""
        self._client_processes.pop(client.id, None)

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
            except Exception as e:
                logger.debug(f"Could not parse Origin header '{origin_header}': {e}")

        # Fall back to Referer header
        referer_header = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if referer_header:
            try:
                parsed = urlparse(referer_header)
                if parsed.netloc:
                    return parsed.netloc
            except Exception as e:
                logger.debug(f"Could not parse Referer header '{referer_header}': {e}")

        return None

    def _build_client_info(self, flow: http.HTTPFlow) -> dict | None:
        """Build client info dict from flow metadata.

        Returns a dict with process info (pid, bundle_id, name) and
        hierarchical filter metadata (app_type, host_origin, referrer_origin),
        or None if no client process info is available.
        """
        client_process: ClientProcess | None = flow.metadata.get("oximy_client")
        if not client_process:
            return None

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

        # Add referrer origin from headers
        referrer_origin = self._extract_request_origin(flow)
        if referrer_origin:
            client_info["referrer_origin"] = referrer_origin

        return client_info

    # =========================================================================
    # TLS Hooks
    # =========================================================================

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """Passthrough check - skip TLS interception for non-whitelisted and pinned hosts.

        PERFORMANCE CRITICAL: This runs on EVERY TLS connection.
        By skipping TLS interception for non-whitelisted domains, we avoid:
        - Certificate generation overhead
        - TLS decrypt/re-encrypt overhead
        This can improve throughput by 20-30% for general browsing.
        """
        if not self._enabled:
            return

        # Sensor disabled - passthrough ALL TLS connections (no interception)
        if not _state.sensor_active:
            data.ignore_connection = True
            return

        host = data.client_hello.sni or (data.context.server.address[0] if data.context.server.address else None)
        if not host:
            return

        # Skip TLS interception for non-whitelisted domains (HUGE performance win)
        # This avoids cert generation + decrypt/re-encrypt for 99% of traffic
        if not matches_domain(host, self._whitelist):
            data.ignore_connection = True
            return

        # Also skip for learned passthrough patterns (cert-pinned hosts)
        if self._tls and self._tls.should_passthrough(host):
            data.ignore_connection = True

    def tls_failed_client(self, data: tls.TlsData) -> None:
        """Learn certificate-pinned hosts from TLS failures."""
        if not self._enabled or not self._tls:
            return
        if not _state.sensor_active:
            return  # Sensor disabled - don't record failures

        host = data.context.server.sni or (data.context.server.address[0] if data.context.server.address else None)
        if host:
            error = str(data.conn.error) if data.conn.error else ""
            self._tls.record_tls_failure(host, error, self._whitelist)

    # =========================================================================
    # HTTP Hooks
    # =========================================================================

    async def request(self, flow: http.HTTPFlow) -> None:
        """Check hierarchical filters on request.

        Filter hierarchy (optimized for performance):
        1. Whitelist check FIRST (fast, filters 99%+ of traffic)
        2. Blacklist check (fast)
        3. App Origin Check (requires process resolution - only for whitelisted)
        4. Host Origin Check (for browser apps only)
        """
        if not self._enabled:
            return
        if not _state.sensor_active:
            return  # Sensor disabled - passthrough all traffic

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Get config snapshot for thread-safe filtering
        config = self._get_config_snapshot()

        # =====================================================================
        # STEP 1: Whitelist check FIRST (fast - filters out 99%+ of traffic)
        # =====================================================================
        if not matches_whitelist(host, path, config["whitelist"]):
            flow.metadata["oximy_skip"] = True
            flow.metadata["oximy_skip_reason"] = "not_whitelisted"
            return

        # Log only for whitelisted requests (99% of traffic skips this)
        logger.debug(f">>> {flow.request.method} {url[:100]}")

        # =====================================================================
        # STEP 2: Blacklist check on URL (fast)
        # =====================================================================
        if word := self._check_blacklist(url, blacklist=config["blacklist"]):
            logger.debug(f"[BLACKLISTED] {url[:80]} (matched: {word})")
            flow.metadata["oximy_skip"] = True
            flow.metadata["oximy_skip_reason"] = "blacklisted"
            return

        # =====================================================================
        # STEP 3: GraphQL operation blacklist check (for /graphql endpoints)
        # =====================================================================
        if path.endswith('/graphql') or '/graphql' in path:
            operation_name = extract_graphql_operation(flow.request.content)
            if operation_name:
                flow.metadata["oximy_graphql_op"] = operation_name
                if word := self._check_blacklist(operation_name, blacklist=config["blacklist"]):
                    logger.debug(f"[BLACKLISTED_GRAPHQL] {operation_name} (matched: {word})")
                    flow.metadata["oximy_skip"] = True
                    flow.metadata["oximy_skip_reason"] = "blacklisted_graphql"
                    return

        # =====================================================================
        # STEP 4: Resolve client process (only for whitelisted requests)
        # First: try connection-time cache (most reliable, populated by client_connected hook)
        # Fallback: lsof lookup if not in cache
        # =====================================================================
        client_process: ClientProcess | None = None

        # First: try connection-time cache (most reliable)
        if flow.client_conn and flow.client_conn.id in self._client_processes:
            client_process = self._client_processes[flow.client_conn.id]
            logger.debug(f"[PROCESS] Using cached: {client_process.name} (bundle: {client_process.bundle_id})")

        # Fallback: lsof lookup if not in cache
        elif self._resolver and flow.client_conn and flow.client_conn.peername:
            try:
                client_port = flow.client_conn.peername[1]
                client_process = await self._resolver.get_process_for_port(client_port)
                logger.debug(f"[PROCESS] lsof lookup: {client_process.name} (bundle: {client_process.bundle_id})")
            except Exception as e:
                logger.debug(f"[PROCESS] lsof fallback failed: {e}")

        if client_process:
            flow.metadata["oximy_client"] = client_process

        # =====================================================================
        # STEP 5: App Origin Check (Layer 1)
        # =====================================================================
        bundle_id = client_process.bundle_id if client_process else None
        logger.debug(f"[APP_CHECK] bundle_id={bundle_id}")
        app_type = matches_app_origin(
            bundle_id,
            config["allowed_app_hosts"],
            config["allowed_app_non_hosts"],
        )

        # Fallback: if no match, determine app type by User-Agent heuristic
        if app_type is None:
            user_agent = flow.request.headers.get("User-Agent", "").lower()
            if any(browser in user_agent for browser in ("chrome", "firefox", "safari", "edge", "mozilla")):
                app_type = "host"
                logger.info(f"[APP_FALLBACK] bundle_id={bundle_id} unmatched but User-Agent looks like browser, treating as host")
            else:
                app_type = "non_host"
                logger.info(f"[APP_FALLBACK] bundle_id={bundle_id} unmatched, defaulting to non_host")

        flow.metadata["oximy_app_type"] = app_type

        # =====================================================================
        # STEP 6: Host Origin Check (Layer 2) - only for "host" (browser) apps
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
        # Mark for capture
        # =====================================================================
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_start"] = time.time()
        # Save request body now — stream_large_bodies may discard it before response hook
        if flow.request.content:
            flow.metadata["oximy_request_body"] = flow.request.content
        logger.debug(f"[CAPTURE] {url[:80]} (app_type={app_type})")

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Enable streaming for SSE responses to prevent client timeouts.

        Uses a filter function instead of True so we can accumulate chunks
        for trace capture while still streaming data through to the client.
        """
        if not flow.response:
            return

        content_type = flow.response.headers.get("content-type", "")
        host = flow.request.pretty_host
        should_stream = False

        # Stream any text/event-stream response
        if "text/event-stream" in content_type:
            should_stream = True

        # Stream known AI API endpoints when response looks like streaming
        if not should_stream and any(h in host for h in ("api.anthropic.com", "api.openai.com")):
            if "stream" in flow.request.url or content_type in ("", "application/octet-stream"):
                should_stream = True

        if should_stream:
            chunks: list[bytes] = []
            accumulated_size = [0]
            flow.metadata["oximy_stream_chunks"] = chunks

            def stream_filter(data: bytes) -> bytes:
                accumulated_size[0] += len(data)
                if accumulated_size[0] <= _MAX_STREAM_CAPTURE_BYTES:
                    chunks.append(data)
                elif not flow.metadata.get("oximy_stream_truncated"):
                    flow.metadata["oximy_stream_truncated"] = True
                    logger.warning(
                        f"[STREAM] Capture truncated at {_MAX_STREAM_CAPTURE_BYTES // (1024*1024)}MB "
                        f"for {host}{flow.request.path}"
                    )
                return data

            flow.response.stream = stream_filter
            logger.debug(f"[STREAM] Enabled for {host}{flow.request.path}")

    def response(self, flow: http.HTTPFlow) -> None:
        """Write trace for captured response."""
        if not self._enabled:
            return
        if not _state.sensor_active:
            return  # Sensor disabled - skip trace writing

        if not flow.response:
            return

        # Handle WebSocket upgrade (101 Switching Protocols) separately
        if flow.response.status_code == 101:
            logger.debug(f"[101_DETECTED] {flow.request.pretty_host}{flow.request.path} - flow.websocket={flow.websocket is not None}")
            self._handle_websocket_upgrade(flow)
            return

        # EARLY EXIT: Skip expensive operations for non-captured requests
        # This check MUST happen BEFORE normalize_body and _build_event
        if flow.metadata.get("oximy_skip"):
            skip_reason = flow.metadata.get("oximy_skip_reason", "unknown")
            logger.info(f"[SKIP] {flow.request.pretty_host}{flow.request.path} - reason: {skip_reason}")
            return

        # Log when requests pass all filters and will be captured
        logger.info(f"[CAPTURE] {flow.request.pretty_host}{flow.request.path}")

        # Only do expensive operations for captured (whitelisted) requests
        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # For streamed responses, reconstruct body from accumulated chunks
        stream_chunks = flow.metadata.get("oximy_stream_chunks")
        if stream_chunks is not None:
            if flow.metadata.get("oximy_stream_truncated"):
                logger.warning(f"[STREAM] Skipping trace for truncated stream: {url[:80]}")
                return
            full_body = b"".join(stream_chunks)
            content_type = flow.response.headers.get("content-type", "")
            response_body = normalize_body(full_body, content_type)
            event = self._build_event(flow, response_body)
            if self._debug_writer:
                self._debug_writer.write(event)
            if self._write_to_buffer(event):
                logger.debug(f"<<< CAPTURED (streamed): {flow.request.method} {url[:80]} [{flow.response.status_code}]")
                self._maybe_upload()
            return

        content_type = flow.response.headers.get("content-type", "")
        response_body = normalize_body(flow.response.content, content_type)
        event = self._build_event(flow, response_body)

        # Write to debug log (only for captured requests now)
        if self._debug_writer:
            self._debug_writer.write(event)

        # Write to memory buffer (cloud-first ingestion)
        if self._write_to_buffer(event):
            graphql_op = flow.metadata.get("oximy_graphql_op", "")
            op_suffix = f" op={graphql_op}" if graphql_op else ""
            logger.debug(f"<<< CAPTURED: {flow.request.method} {url[:80]} [{flow.response.status_code}]{op_suffix}")

            # Check if we should upload to API
            self._maybe_upload()

    def _handle_websocket_upgrade(self, flow: http.HTTPFlow) -> None:
        """Handle WebSocket upgrade (101 Switching Protocols) response."""
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

        # Add client info (includes referrer_origin from headers)
        client_info = self._build_client_info(flow)
        if client_info:
            event["client"] = client_info

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

        # Skip writing to main traces if marked by filters
        if flow.metadata.get("oximy_skip"):
            logger.debug(f"[WS_UPGRADE_SKIP] {url} - skipped due to: {flow.metadata.get('oximy_skip_reason', 'unknown')}")
            return

        # Write to memory buffer (cloud-first ingestion)
        if self._write_to_buffer(event):
            logger.debug(f"<<< CAPTURED WS_UPGRADE: {flow.request.method} {url[:80]} [101]")

            # Check if we should upload to API
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
                    # Bit 1 (value 2) and bit 2 (value 4) indicate stream end
                    # Include all combinations: 2-7 (with bit 1 or 2), 10-15 (with bit 3)
                    stream_end_flags = {2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15}
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

        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Could not parse WebSocket message for turn completion: {e}")
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

        # Add client info (includes referrer_origin from headers)
        client_info = self._build_client_info(flow)
        if client_info:
            event["client"] = client_info

        # Add WebSocket-specific fields
        event["host"] = host
        event["path"] = path
        event["messages"] = ws_messages
        event["timing"] = {"message_count": len(ws_messages)}

        # Write to debug log (unfiltered)
        if self._debug_writer:
            self._debug_writer.write(event)

        # Write to memory buffer (cloud-first ingestion)
        if self._write_to_buffer(event):
            logger.debug(f"<<< CAPTURED WS_TURN: {host} ({len(ws_messages)} messages)")
            self._maybe_upload()

        # Clear buffer for next turn
        flow.metadata["oximy_ws_messages"] = []
        flow.metadata["oximy_ws_message_count"] = 0

    def _build_event(self, flow: http.HTTPFlow, response_body: str) -> dict:
        """Build trace event."""
        request_content = flow.request.content or flow.metadata.get("oximy_request_body")
        request_body = normalize_body(request_content) if request_content else None

        duration_ms = ttfb_ms = None
        if flow.request.timestamp_start and flow.response:
            if flow.response.timestamp_end:
                duration_ms = int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000)
            if flow.response.timestamp_start:
                ttfb_ms = int((flow.response.timestamp_start - flow.request.timestamp_start) * 1000)

        # Filter out cookie headers for privacy
        request_headers = {k: v for k, v in flow.request.headers.items() if k.lower() != "cookie"}
        response_headers = {k: v for k, v in flow.response.headers.items() if k.lower() != "set-cookie"} if flow.response else {}

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "http",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info (includes referrer_origin from headers)
        client_info = self._build_client_info(flow)
        if client_info:
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
        if not _state.sensor_active:
            return  # Sensor disabled - skip WebSocket tracking

        host = flow.request.pretty_host
        path = flow.request.path
        logger.debug(f"[WS_START] {host}{path} - WebSocket connection established, flow.websocket={flow.websocket is not None}")

        # Initialize message tracking in metadata
        flow.metadata["oximy_ws_messages"] = []
        flow.metadata["oximy_ws_start"] = time.time()
        flow.metadata["oximy_ws_message_count"] = 0

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Capture WebSocket messages in real-time."""
        if not self._enabled:
            return
        if not _state.sensor_active:
            return  # Sensor disabled - skip message capture

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

        logger.debug(f"[WS_MESSAGE] {url} - {direction} message (text={is_text}, size={len(content)} chars)")

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

            # Accumulate for aggregate events (with limit to prevent memory leak)
            MAX_WS_MESSAGES_PER_TURN = 1000
            if "oximy_ws_messages" not in flow.metadata:
                flow.metadata["oximy_ws_messages"] = []
            ws_messages = flow.metadata["oximy_ws_messages"]
            if len(ws_messages) >= MAX_WS_MESSAGES_PER_TURN:
                # Keep newest messages, discard oldest
                flow.metadata["oximy_ws_messages"] = ws_messages[-(MAX_WS_MESSAGES_PER_TURN - 1):]
                logger.debug(f"WebSocket message buffer full, discarding oldest messages")
            flow.metadata["oximy_ws_messages"].append(message_data)
            flow.metadata["oximy_ws_message_count"] = current_count

            logger.debug(f"[WS_MESSAGE_CAPTURED] {url} - message #{current_count} from {direction}: {content[:100]}")

            # Check for completion signals in server messages and write aggregate
            if not msg.from_client and self._is_ws_turn_complete(content):
                logger.debug(f"[WS_TURN_COMPLETE] {url} - detected completion signal, writing aggregate")
                self._write_ws_turn_aggregate(flow)

    def websocket_end(self, flow: http.HTTPFlow) -> None:
        """Write WebSocket trace on connection close."""
        if not self._enabled:
            return
        if not _state.sensor_active:
            return  # Sensor disabled - skip final trace write

        host = flow.request.pretty_host
        path = flow.request.path
        url = f"{host}{path}"

        # Try to get messages from flow.websocket.messages directly (mitmproxy stores them)
        ws_messages = []
        if flow.websocket and flow.websocket.messages:
            logger.debug(f"[WS_END] {url} - found {len(flow.websocket.messages)} messages in flow.websocket")
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

        logger.debug(f"[WS_END] {host}{path} - connection closed, accumulated {len(ws_messages)} messages")

        if not ws_messages:
            logger.debug(f"[WS_END_SKIP] {host}{path} - no messages to write")
            return

        start = flow.metadata.get("oximy_ws_start", time.time())

        event: dict = {
            "event_id": generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "websocket",
        }

        if self._device_id:
            event["device_id"] = self._device_id

        # Add client info (includes referrer_origin from headers)
        client_info = self._build_client_info(flow)
        if client_info:
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

        # Write to memory buffer (cloud-first ingestion)
        if self._write_to_buffer(event):
            logger.debug(f"<<< CAPTURED WS: {flow.request.pretty_host} ({len(ws_messages)} messages)")

            # Check if we should upload to API
            self._maybe_upload()

    # =========================================================================
    # Upload Trigger
    # =========================================================================

    def _maybe_upload(self) -> None:
        """Upload traces from memory buffer if threshold reached.

        Cloud-first: uploads directly from memory buffer to API.
        Falls back to disk only if buffer is full and API is unreachable.

        Designed for scalability: with longer intervals (e.g., 30s), uploads
        ALL available batches when the interval fires, not just one.
        """
        if not self._direct_uploader or not self._buffer:
            return

        # Skip regular uploads when sensor is disabled
        # (Any pending traces were flushed when sensor was disabled)
        if not _state.sensor_active:
            return

        now = time.time()
        time_elapsed = now - self._last_upload_time >= self._upload_interval_seconds
        count_reached = self._traces_since_upload >= self._upload_threshold_count

        if (time_elapsed or count_reached) and self._buffer.size() > 0:
            try:
                # Upload ALL available batches (important for longer intervals like 30s)
                upload_failed = False
                batches_uploaded = 0
                traces_before = self._buffer.size()
                while self._buffer.size() > 0:
                    success = self._direct_uploader.upload_batch()
                    if success:
                        batches_uploaded += 1
                    else:
                        upload_failed = True
                        break

                if batches_uploaded > 0:
                    self._last_upload_time = now
                    self._traces_since_upload = 0
                    # Log multi-batch uploads (useful for monitoring at longer intervals)
                    if batches_uploaded > 1:
                        logger.debug(f"Multi-batch upload: {batches_uploaded} batches, {traces_before} traces")

                if upload_failed:
                    # Upload failed - check if we need emergency disk fallback
                    # Only write to disk if buffer is getting dangerously full (>80% capacity)
                    buffer_capacity = self._buffer.max_bytes
                    if self._buffer.bytes_used() > (buffer_capacity * 0.8):
                        logger.warning(f"Buffer >80% full ({self._buffer.bytes_used()}/{buffer_capacity} bytes) and upload failing, emergency disk write")
                        writer = self._ensure_writer()
                        if writer:
                            # Write oldest traces to disk to free buffer space
                            for event in self._buffer.take_batch(5 * 1024 * 1024):  # 5MB batch
                                writer.write(event)

            except Exception as e:
                logger.warning(f"Failed to upload traces: {e}")

    def upload_all_traces(self) -> dict[str, int]:
        """Upload all pending traces (memory buffer and disk fallback).

        Called by remote command execution (force_sync).

        Returns:
            dict with keys: eventsUploaded (int), bytesUploaded (int)
        """
        total_uploaded = 0
        total_bytes = 0

        try:
            # Upload from memory buffer first
            if self._direct_uploader and self._buffer and self._buffer.size() > 0:
                uploaded_count = self._direct_uploader.upload_all()
                if uploaded_count > 0:
                    total_uploaded += uploaded_count
                    # Estimate bytes (rough approximation)
                    total_bytes += uploaded_count * 500  # ~500 bytes per trace avg
                    logger.info(f"Force sync: uploaded {uploaded_count} traces from memory buffer")

            # Upload from disk fallback files
            if self._uploader and self._output_dir:
                # Flush writer first if active
                if self._writer and self._writer._fo:
                    self._writer._fo.flush()
                # Pass active file to avoid deleting file currently being written
                active_file = self._writer._current_file if self._writer else None
                uploaded = self._uploader.upload_all_pending(self._output_dir, active_file=active_file)
                if uploaded > 0:
                    total_uploaded += uploaded
                    # Estimate bytes (rough approximation)
                    total_bytes += uploaded * 500  # ~500 bytes per trace avg
                    logger.info(f"Force sync: uploaded {uploaded} traces from disk fallback")
        except Exception as e:
            logger.warning(f"upload_all_traces failed: {e}")

        return {"eventsUploaded": total_uploaded, "bytesUploaded": total_bytes}

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

        # Remove terminal env injections (shell profiles, env scripts, CA bundle)
        _teardown_terminal_env()

        # ALWAYS disable system proxy on Windows to prevent orphaned proxy
        # On macOS, only disable if we enabled it (host app may manage proxy)
        with _state.lock:
            _delete_proxy_port_file()
            if sys.platform == "win32":
                _set_system_proxy(enable=False)
                _state.proxy_active = False
                _write_proxy_state()
            elif _addon_manages_proxy:
                _set_system_proxy(enable=False)
                _state.proxy_active = False
                _write_proxy_state()

        # Cloud-first: try to upload remaining traces from memory buffer
        if self._buffer and self._buffer.size() > 0:
            logger.info(f"Shutdown: {self._buffer.size()} traces in buffer, attempting final upload")
            if self._direct_uploader:
                try:
                    success = self._direct_uploader.upload_all()
                    if success:
                        logger.info("Successfully uploaded all buffered traces on shutdown")
                    else:
                        # Upload failed - emergency write to disk
                        logger.warning("Final upload failed, writing remaining traces to disk")
                        writer = self._ensure_writer()
                        if writer:
                            for event in self._buffer.peek_all():
                                writer.write(event)
                            self._buffer.clear()
                            logger.info(f"Emergency disk write complete")
                except Exception as e:
                    logger.warning(f"Failed to upload buffered traces on shutdown: {e}")
                    # Emergency fallback to disk
                    writer = self._ensure_writer()
                    if writer:
                        for event in self._buffer.peek_all():
                            writer.write(event)
                        self._buffer.clear()

        # Close writers to flush pending writes
        if self._writer:
            self._writer.close()
            self._writer = None
        if self._debug_writer:
            self._debug_writer.close()
            self._debug_writer = None

        # Upload any leftover JSONL files from emergency disk writes
        # (and delete them after successful upload - writer is closed so no active file)
        if self._uploader and self._output_dir:
            try:
                uploaded = self._uploader.upload_all_pending(self._output_dir, active_file=None)
                if uploaded > 0:
                    logger.info(f"Uploaded {uploaded} traces from disk fallback files on shutdown")
            except Exception as e:
                logger.warning(f"Failed to upload disk fallback traces on shutdown: {e}")

        self._enabled = False
        logger.info("Oximy addon disabled")


addons = [
    OximyAddon(),
]
