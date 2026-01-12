"""
TLS Passthrough for certificate-pinned hosts.

Handles hosts that use certificate pinning (like Apple services) by:
1. Pre-configuring known pinned hosts for immediate passthrough
2. Auto-learning new pinned hosts when TLS handshake fails
3. Persisting learned hosts across restarts
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mitmproxy import tls

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.process import ClientProcess

logger = logging.getLogger(__name__)

# Known certificate-pinned domains (regex patterns)
# These are hosts that will NEVER work with MITM interception
KNOWN_PINNED_HOSTS = [
    # Apple services - extensive certificate pinning
    r".*\.apple\.com$",
    r".*\.icloud\.com$",
    r".*\.itunes\.com$",
    r".*\.mzstatic\.com$",
    r".*\.apple-cloudkit\.com$",
    # Google certificate transparency / pinned services
    r".*\.googleapis\.com$",  # Some Google APIs are pinned
    r"accounts\.google\.com$",
    # Banking/Financial (commonly pinned)
    # Add specific ones as discovered
    # Other known pinners
    r".*\.pinning\.test$",  # For testing
]


class TLSPassthrough:
    """
    Manages TLS passthrough for certificate-pinned hosts.

    Integrates with OximyAddon to:
    - Skip interception for known pinned hosts
    - Auto-learn new pinned hosts from TLS failures
    - Log when hosts are bypassed (for visibility)
    """

    def __init__(self, persist_path: Path | None = None):
        """
        Args:
            persist_path: Optional path to persist learned hosts across restarts
        """
        self._known_patterns: list[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in KNOWN_PINNED_HOSTS
        ]
        self._learned_hosts: set[str] = set()  # Exact hostnames that failed
        self._persist_path = persist_path
        self._process_resolver = None  # Set by OximyAddon if available

        # Load persisted hosts
        if persist_path:
            self._load_persisted()

    def set_process_resolver(self, resolver) -> None:
        """Set the process resolver for client attribution in logs."""
        self._process_resolver = resolver

    def should_passthrough(self, host: str) -> tuple[bool, str | None]:
        """
        Check if a host should bypass TLS interception.

        Returns:
            (should_passthrough, reason) - reason is None if not passthrough
        """
        # Check known patterns first
        for pattern in self._known_patterns:
            if pattern.match(host):
                return True, "known_pinned"

        # Check learned hosts
        if host in self._learned_hosts:
            return True, "learned_pinned"

        return False, None

    def record_tls_failure(
        self, host: str, error: str, client_process: ClientProcess | None = None
    ) -> bool:
        """
        Record a TLS handshake failure and determine if it's certificate pinning.

        Returns:
            True if this was likely certificate pinning (host added to passthrough)
        """
        # Patterns that indicate certificate pinning
        pinning_indicators = [
            "certificate verify failed",
            "unknown ca",
            "bad certificate",
            "certificate_unknown",
            "self signed certificate",
            "unable to get local issuer certificate",
            # Client disconnected during handshake often means pinning
            "client disconnected during the handshake",
        ]

        error_lower = error.lower()
        is_pinning = any(indicator in error_lower for indicator in pinning_indicators)

        if is_pinning and host not in self._learned_hosts:
            self._learned_hosts.add(host)
            self._persist()

            # Build client info for logging
            client_str = ""
            if client_process and client_process.name:
                client_str = f" (client: {client_process.name}"
                if client_process.pid:
                    client_str += f" PID:{client_process.pid}"
                client_str += ")"

            logger.warning(
                f"🔒 Certificate pinning detected: {host}{client_str} - "
                f"added to passthrough list. Future connections will bypass interception."
            )
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
                logger.info(
                    f"Loaded {len(self._learned_hosts)} learned pinned hosts from cache"
                )
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

    def get_stats(self) -> dict:
        """Get statistics about passthrough state."""
        return {
            "known_patterns": len(self._known_patterns),
            "learned_hosts": len(self._learned_hosts),
            "learned_list": sorted(self._learned_hosts),
        }

    # -------------------------------------------------------------------------
    # Mitmproxy TLS Hooks
    # -------------------------------------------------------------------------

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """
        Called when a TLS ClientHello is received.

        If the host is known to be pinned, skip interception immediately.
        """
        # Get the server hostname (SNI or address)
        server = data.context.server
        host = data.client_hello.sni or (server.address[0] if server.address else None)

        if not host:
            return

        should_pass, reason = self.should_passthrough(host)

        if should_pass:
            data.ignore_connection = True

            # Log based on reason
            if reason == "known_pinned":
                logger.debug(f"⏭️  TLS passthrough (known pinned): {host}")
            else:
                logger.info(f"⏭️  TLS passthrough (previously failed): {host}")

    def tls_failed_client(self, data: tls.TlsData) -> None:
        """
        Called when TLS handshake with client fails.

        This is our signal that certificate pinning may be in play.
        """
        server = data.context.server
        host = server.sni or (server.address[0] if server.address else None)

        if not host:
            return

        # Get error message
        error = str(data.conn.error) if data.conn.error else "unknown error"

        # Try to get client process info for better logging
        client_process = None
        if self._process_resolver:
            try:
                client_addr = data.context.client.peername
                if client_addr:
                    client_process = self._process_resolver.get_process_for_port(
                        client_addr[1]
                    )
            except Exception:
                pass  # Best effort

        self.record_tls_failure(host, error, client_process)


# Singleton for use as mitmproxy addon
_passthrough_instance: TLSPassthrough | None = None


def get_passthrough(persist_path: Path | None = None) -> TLSPassthrough:
    """Get or create the TLS passthrough singleton."""
    global _passthrough_instance
    if _passthrough_instance is None:
        _passthrough_instance = TLSPassthrough(persist_path)
    return _passthrough_instance
