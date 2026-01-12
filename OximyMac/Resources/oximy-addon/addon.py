"""
Main Oximy addon for mitmproxy.

Captures AI API traffic based on OISP bundle whitelists,
normalizes events, and writes to JSONL files.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from bundle import BundleLoader
from bundle import DEFAULT_BUNDLE_URL
from matcher import TrafficMatcher
from models import EventSource
from models import EventTiming
from models import Interaction
from models import MatchResult
from models import OximyEvent
from parser import RequestParser
from parser import ResponseParser
from passthrough import TLSPassthrough
from process import ClientProcess
from process import ProcessResolver
from sse import create_sse_stream_handler
from sse import is_sse_response
from sse import SSEBuffer
from writer import EventWriter

from mitmproxy import ctx
from mitmproxy import http

if TYPE_CHECKING:
    from bundle import OISPBundle

logger = logging.getLogger(__name__)


class _SuppressDisconnectFilter(logging.Filter):
    """Filter out noisy 'client disconnect' and 'server disconnect' messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Suppress generic disconnect messages (but keep TLS failure messages)
        if (
            msg == "client disconnect"
            or msg.startswith("server disconnect ")
            or msg.startswith("client connect")
            or msg.startswith("server connect")
        ):
            return False
        return True


# Apply filter to mitmproxy's proxy logger
logging.getLogger("mitmproxy.proxy.server").addFilter(_SuppressDisconnectFilter())

# Metadata keys for storing data on flows
OXIMY_METADATA_KEY = "oximy_match"
OXIMY_CLIENT_KEY = "oximy_client"

# -------------------------------------------------------------------------
# macOS System Proxy Configuration (Development Only)
# Set OXIMY_AUTO_PROXY=1 to enable automatic proxy setup/teardown
# Comment out or set to 0 for production deployments
# -------------------------------------------------------------------------
# DISABLED: OximyMac app handles proxy setup via ProxyService.swift
# Setting this to True would conflict with the app's proxy management
OXIMY_AUTO_PROXY_ENABLED = False  # Disabled - app manages proxy
OXIMY_PROXY_HOST = "127.0.0.1"
OXIMY_PROXY_PORT = "8088"  # Not used when OXIMY_AUTO_PROXY_ENABLED=False
OXIMY_NETWORK_SERVICE = "Wi-Fi"  # Not used when OXIMY_AUTO_PROXY_ENABLED=False


def _set_macos_proxy(enable: bool) -> None:
    """
    Enable or disable macOS system proxy settings.

    This is a development convenience - comment out OXIMY_AUTO_PROXY_ENABLED
    for production deployments where proxy should be managed externally.
    """
    if sys.platform != "darwin" or not OXIMY_AUTO_PROXY_ENABLED:
        return

    try:
        if enable:
            # Enable HTTPS proxy
            subprocess.run(
                [
                    "networksetup",
                    "-setsecurewebproxy",
                    OXIMY_NETWORK_SERVICE,
                    OXIMY_PROXY_HOST,
                    OXIMY_PROXY_PORT,
                ],
                check=True,
                capture_output=True,
            )
            # Enable HTTP proxy
            subprocess.run(
                [
                    "networksetup",
                    "-setwebproxy",
                    OXIMY_NETWORK_SERVICE,
                    OXIMY_PROXY_HOST,
                    OXIMY_PROXY_PORT,
                ],
                check=True,
                capture_output=True,
            )
            logger.info(f"System proxy enabled: {OXIMY_PROXY_HOST}:{OXIMY_PROXY_PORT}")
        else:
            # Disable HTTPS proxy
            subprocess.run(
                [
                    "networksetup",
                    "-setsecurewebproxystate",
                    OXIMY_NETWORK_SERVICE,
                    "off",
                ],
                check=True,
                capture_output=True,
            )
            # Disable HTTP proxy
            subprocess.run(
                ["networksetup", "-setwebproxystate", OXIMY_NETWORK_SERVICE, "off"],
                check=True,
                capture_output=True,
            )
            logger.info("System proxy disabled")
    except subprocess.CalledProcessError as e:
        logger.warning(
            f"Failed to {'enable' if enable else 'disable'} system proxy: {e}"
        )
    except FileNotFoundError:
        logger.warning("networksetup command not found - not on macOS?")


class OximyAddon:
    """
    Mitmproxy addon that captures AI API traffic.

    Usage:
        mitmdump -s path/to/oximy/__init__.py --set oximy_enabled=true

    Or load programmatically:
        from mitmproxy.addons.oximy import OximyAddon
        addons = [OximyAddon()]
    """

    def __init__(self):
        self._bundle_loader: BundleLoader | None = None
        self._bundle: OISPBundle | None = None
        self._matcher: TrafficMatcher | None = None
        self._request_parser: RequestParser | None = None
        self._response_parser: ResponseParser | None = None
        self._writer: EventWriter | None = None
        self._process_resolver: ProcessResolver | None = None
        self._tls_passthrough: TLSPassthrough | None = None
        self._sse_buffers: dict[str, SSEBuffer] = {}
        self._enabled: bool = False

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option(
            name="oximy_enabled",
            typespec=bool,
            default=False,
            help="Enable OISP traffic capture",
        )
        loader.add_option(
            name="oximy_output_dir",
            typespec=str,
            default="~/.oximy/traces",
            help="Directory for output JSONL files",
        )
        loader.add_option(
            name="oximy_bundle_url",
            typespec=str,
            default=DEFAULT_BUNDLE_URL,
            help="URL of the OISP bundle JSON",
        )
        loader.add_option(
            name="oximy_bundle_cache_minutes",
            typespec=int,
            default=30,
            help="Bundle cache expiry in minutes (default: 30). Bundle is re-fetched from URL when cache expires.",
        )
        loader.add_option(
            name="oximy_include_raw",
            typespec=bool,
            default=True,
            help="Include raw request/response bodies in events",
        )

    def configure(self, updated: set[str]) -> None:
        """Handle configuration changes."""
        # Check if we need to (re)initialize
        relevant_options = {"oximy_enabled", "oximy_bundle_url", "oximy_output_dir"}
        if not relevant_options.intersection(updated):
            return

        new_enabled = ctx.options.oximy_enabled
        logger.info(f"Oximy configure: oximy_enabled={new_enabled}")

        # Handle disable
        if not new_enabled:
            if self._enabled:
                logger.info("Oximy addon disabled")
                self._cleanup()
            self._enabled = False
            return

        self._enabled = True

        # Convert minutes to hours for BundleLoader cache expiry
        cache_minutes = ctx.options.oximy_bundle_cache_minutes
        cache_hours = cache_minutes / 60.0

        # Initialize bundle loader
        self._bundle_loader = BundleLoader(
            bundle_url=ctx.options.oximy_bundle_url,
            max_age_hours=cache_hours,
        )

        try:
            self._bundle = self._bundle_loader.load()
            logger.info(f"Loaded OISP bundle version {self._bundle.bundle_version}")
        except RuntimeError as e:
            logger.error(f"Failed to load OISP bundle: {e}")
            self._enabled = False
            return

        # Initialize matcher
        self._matcher = TrafficMatcher(self._bundle)

        # Initialize parsers
        self._request_parser = RequestParser(self._bundle.parsers)
        self._response_parser = ResponseParser(self._bundle.parsers)

        # Initialize writer
        output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = EventWriter(output_dir)

        # Initialize process resolver for client attribution
        self._process_resolver = ProcessResolver()

        # Initialize TLS passthrough for certificate-pinned hosts
        passthrough_cache = output_dir / "pinned_hosts.json"
        self._tls_passthrough = TLSPassthrough(persist_path=passthrough_cache)
        self._tls_passthrough.set_process_resolver(self._process_resolver)

        # Enable system proxy (development convenience)
        _set_macos_proxy(enable=True)

        # Bundle refresh is handled by cache expiry in BundleLoader
        # When cache expires (default: 30 min), bundle is re-fetched from URL on next request

        logger.info(f"Oximy addon enabled, writing to {output_dir} (bundle cache: {cache_minutes} min)")

    def request(self, flow: http.HTTPFlow) -> None:
        """Classify incoming requests and capture client process info."""
        if not self._enabled or not self._matcher:
            return

        # Match the flow
        match_result = self._matcher.match(flow)

        # Store result in flow metadata
        flow.metadata[OXIMY_METADATA_KEY] = match_result

        # Capture client process info IMMEDIATELY on request
        # This must happen as early as possible to avoid race conditions
        # where the client process exits before we can query it
        if match_result.classification != "drop" and self._process_resolver:
            client_port = flow.client_conn.peername[1]
            client_process = self._process_resolver.get_process_for_port(client_port)
            flow.metadata[OXIMY_CLIENT_KEY] = client_process
            logger.debug(
                f"Client process: {client_process.name} (PID {client_process.pid})"
            )

        if match_result.classification != "drop":
            logger.debug(
                f"Matched: {flow.request.pretty_host} -> "
                f"{match_result.classification} ({match_result.source_id})"
            )

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Set up SSE streaming if needed."""
        if not self._enabled:
            return

        match_result: MatchResult | None = flow.metadata.get(OXIMY_METADATA_KEY)
        if not match_result or match_result.classification == "drop":
            return

        # Check if this is an SSE response
        if flow.response and is_sse_response(flow.response.headers):
            logger.debug(f"Setting up SSE buffer for {flow.id}")
            buffer = SSEBuffer(api_format=match_result.api_format)
            self._sse_buffers[flow.id] = buffer

            # Set up streaming to capture chunks - this is the key fix!
            # The stream handler intercepts each chunk, accumulates content,
            # and passes it through unchanged to the client
            flow.response.stream = create_sse_stream_handler(buffer)

    def response(self, flow: http.HTTPFlow) -> None:
        """Process responses and write events."""
        if not self._enabled or not self._writer:
            return

        match_result: MatchResult | None = flow.metadata.get(OXIMY_METADATA_KEY)
        if not match_result or match_result.classification == "drop":
            return

        try:
            event = self._build_event(flow, match_result)
            if event:
                self._writer.write(event)
                self._log_captured_event(event, flow)
        except Exception as e:
            logger.error(f"Failed to process flow: {e}", exc_info=True)
        finally:
            # Clean up SSE buffer
            self._sse_buffers.pop(flow.id, None)

    def _log_captured_event(self, event: OximyEvent, flow: http.HTTPFlow) -> None:
        """Log a nicely formatted summary of captured AI traffic."""
        # Build client info string
        client_str = ""
        if event.client and event.client.name:
            client_str = f" [{event.client.name}]"
            if (
                event.client.parent_name
                and event.client.parent_name != event.client.name
            ):
                client_str = f" [{event.client.parent_name} > {event.client.name}]"

        # Build model info
        model_str = ""
        if event.interaction and event.interaction.model:
            model_str = f" model={event.interaction.model}"

        # Build timing info
        timing_str = ""
        if event.timing.duration_ms:
            timing_str = f" ({event.timing.duration_ms}ms)"

        # Log format: [source_id] METHOD path -> status (timing) [client]
        logger.info(
            f"✓ [{event.source.id}]{client_str} "
            f"{flow.request.method} {flow.request.path[:50]}{'...' if len(flow.request.path) > 50 else ''} "
            f"-> {flow.response.status_code if flow.response else '?'}{model_str}{timing_str}"
        )

    def _build_event(
        self, flow: http.HTTPFlow, match_result: MatchResult
    ) -> OximyEvent | None:
        """Build an OximyEvent from a flow."""
        if not flow.response:
            return None

        # Calculate timing
        timing = self._calculate_timing(flow)

        # Get client process info (captured during request phase)
        client_process: ClientProcess | None = flow.metadata.get(OXIMY_CLIENT_KEY)

        # Build source
        source = EventSource(
            type=match_result.source_type or "api",
            id=match_result.source_id or "unknown",
            endpoint=match_result.endpoint,
        )

        if match_result.classification == "identifiable":
            # Metadata-only event
            return OximyEvent.create(
                source=source,
                trace_level="identifiable",
                timing=timing,
                client=client_process,
                metadata={
                    "request_method": flow.request.method,
                    "request_path": flow.request.path,
                    "response_status": flow.response.status_code,
                    "content_length": len(flow.response.content or b""),
                },
            )

        # Full trace event
        include_raw = ctx.options.oximy_include_raw

        # Parse request
        request_data = None
        if self._request_parser and flow.request.content:
            request_data = self._request_parser.parse(
                flow.request.content,
                match_result.api_format,
                include_raw=include_raw,
            )

        # Parse response
        response_data = None
        sse_buffer = self._sse_buffers.get(flow.id)

        if sse_buffer:
            # Use accumulated SSE data
            sse_result = sse_buffer.finalize()
            from models import InteractionResponse

            response_data = InteractionResponse(
                content=sse_result.get("content"),
                model=sse_result.get("model"),
                finish_reason=sse_result.get("finish_reason"),
                usage=sse_result.get("usage"),
                raw=None,  # Don't include raw for SSE (too large)
            )
        elif self._response_parser and flow.response.content:
            response_data = self._response_parser.parse(
                flow.response.content,
                match_result.api_format,
                include_raw=include_raw,
            )

        if not request_data or not response_data:
            # Can't build full interaction
            return OximyEvent.create(
                source=source,
                trace_level="identifiable",
                timing=timing,
                client=client_process,
                metadata={
                    "request_method": flow.request.method,
                    "request_path": flow.request.path,
                    "response_status": flow.response.status_code,
                    "content_length": len(flow.response.content or b""),
                    "parse_error": "Could not parse request or response",
                },
            )

        # Determine model (prefer response, fall back to request)
        model = response_data.model or (request_data.model if request_data else None)

        interaction = Interaction(
            model=model,
            request=request_data,
            response=response_data,
        )

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
            client=client_process,
            interaction=interaction,
        )

    def _calculate_timing(self, flow: http.HTTPFlow) -> EventTiming:
        """Calculate timing metrics from flow timestamps."""
        duration_ms = None
        ttfb_ms = None

        if flow.request.timestamp_start and flow.response:
            if flow.response.timestamp_end:
                duration_ms = int(
                    (flow.response.timestamp_end - flow.request.timestamp_start) * 1000
                )
            if flow.response.timestamp_start:
                ttfb_ms = int(
                    (flow.response.timestamp_start - flow.request.timestamp_start)
                    * 1000
                )

        return EventTiming(duration_ms=duration_ms, ttfb_ms=ttfb_ms)

    # -------------------------------------------------------------------------
    # TLS Hooks - Handle certificate pinning passthrough
    # -------------------------------------------------------------------------

    def tls_clienthello(self, data) -> None:
        """Check if host should bypass TLS interception."""
        if self._enabled and self._tls_passthrough:
            self._tls_passthrough.tls_clienthello(data)

    def tls_failed_client(self, data) -> None:
        """Record TLS failures to learn certificate-pinned hosts."""
        if self._enabled and self._tls_passthrough:
            self._tls_passthrough.tls_failed_client(data)

    def done(self) -> None:
        """Clean up on shutdown."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        # Disable system proxy (development convenience)
        _set_macos_proxy(enable=False)

        if self._writer:
            self._writer.close()
            self._writer = None

        if self._process_resolver:
            self._process_resolver.clear_cache()
            self._process_resolver = None

        self._tls_passthrough = None
        self._sse_buffers.clear()
        self._matcher = None
        self._request_parser = None
        self._response_parser = None
        self._bundle = None


# For use with `mitmdump -s .../oximy/addon.py`
addons = [OximyAddon()]
