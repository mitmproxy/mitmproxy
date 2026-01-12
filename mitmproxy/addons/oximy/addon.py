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

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.addons.oximy.bundle import BundleLoader
from mitmproxy.addons.oximy.bundle import DEFAULT_BUNDLE_URL
from mitmproxy.addons.oximy.matcher import TrafficMatcher
from mitmproxy.addons.oximy.models import EventSource
from mitmproxy.addons.oximy.models import EventTiming
from mitmproxy.addons.oximy.models import Interaction
from mitmproxy.addons.oximy.models import MatchResult
from mitmproxy.addons.oximy.models import OximyEvent
from mitmproxy.addons.oximy.models import Subscription
from mitmproxy.addons.oximy.parser import analyze_content
from mitmproxy.addons.oximy.parser import ConfigurableRequestParser
from mitmproxy.addons.oximy.parser import ConfigurableStreamBuffer
from mitmproxy.addons.oximy.parser import JSONATA_AVAILABLE
from mitmproxy.addons.oximy.parser import RequestParser
from mitmproxy.addons.oximy.parser import ResponseParser
from mitmproxy.addons.oximy.passthrough import TLSPassthrough
from mitmproxy.addons.oximy.process import ClientProcess
from mitmproxy.addons.oximy.process import ProcessResolver
from mitmproxy.addons.oximy.writer import EventWriter

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.bundle import OISPBundle

# Configure logging to output to stderr (which will be captured by MITMService)
# Set INFO level by default so we can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

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
OXIMY_AUTO_PROXY_ENABLED = True  # Disabled - proxy management handled by OximyMac app
OXIMY_PROXY_HOST = "127.0.0.1"
OXIMY_PROXY_PORT = "8088"
OXIMY_NETWORK_SERVICE = "Wi-Fi"  # Change if using different network interface


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
        self._configurable_request_parser: ConfigurableRequestParser | None = None
        self._writer: EventWriter | None = None
        self._process_resolver: ProcessResolver | None = None
        self._tls_passthrough: TLSPassthrough | None = None
        self._configurable_buffers: dict[str, ConfigurableStreamBuffer] = {}
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
            name="oximy_bundle_refresh_hours",
            typespec=int,
            default=24,
            help="Bundle refresh interval in hours",
        )
        loader.add_option(
            name="oximy_include_raw",
            typespec=bool,
            default=True,
            help="Include raw request/response bodies in events",
        )
        loader.add_option(
            name="oximy_verbose",
            typespec=bool,
            default=False,
            help="Enable verbose/debug logging for troubleshooting",
        )

    def configure(self, updated: set[str]) -> None:
        """Handle configuration changes."""
        # Handle verbose logging toggle
        if "oximy_verbose" in updated:
            if ctx.options.oximy_verbose:
                logging.getLogger("mitmproxy.addons.oximy").setLevel(logging.DEBUG)
                logger.info("Verbose logging ENABLED")
            else:
                logging.getLogger("mitmproxy.addons.oximy").setLevel(logging.INFO)

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

        # Initialize bundle loader
        self._bundle_loader = BundleLoader(
            bundle_url=ctx.options.oximy_bundle_url,
            max_age_hours=ctx.options.oximy_bundle_refresh_hours,
        )

        try:
            self._bundle = self._bundle_loader.load()
            logger.info(f"========== OXIMY ADDON STARTING ==========")
            logger.info(f"OISP Bundle loaded: version {self._bundle.bundle_version}")
            logger.info(f"  - Websites: {len(self._bundle.websites)} sites")
            logger.info(f"  - Apps: {len(self._bundle.apps)} applications")
            logger.info(f"  - Parsers: {len(self._bundle.parsers)} parser configs")
        except RuntimeError as e:
            logger.error(f"========== OXIMY ADDON FAILED TO START ==========")
            logger.error(f"Failed to load OISP bundle: {e}")
            logger.error(f"Bundle URL: {ctx.options.oximy_bundle_url}")
            logger.error("The addon will be DISABLED - no AI traffic will be captured!")
            self._enabled = False
            return
        except Exception as e:
            logger.error(f"========== OXIMY ADDON FAILED TO START ==========")
            logger.error(f"Unexpected error loading bundle: {e}", exc_info=True)
            self._enabled = False
            return

        # Initialize matcher
        self._matcher = TrafficMatcher(self._bundle)

        # Initialize parsers
        self._request_parser = RequestParser(self._bundle.parsers)
        self._response_parser = ResponseParser(self._bundle.parsers)

        # Initialize configurable parser (JSONata-based) if available
        if JSONATA_AVAILABLE:
            self._configurable_request_parser = ConfigurableRequestParser()
            logger.info("JSONata-based configurable parsing enabled")
        else:
            logger.warning("jsonata-python not installed, using legacy parsers only")

        # Initialize writer
        output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = EventWriter(output_dir)

        # Initialize process resolver for client attribution
        self._process_resolver = ProcessResolver()

        # Build bundle_id -> app_id index from registry
        bundle_id_index = self._build_bundle_id_index()
        self._process_resolver.set_bundle_id_index(bundle_id_index)
        if bundle_id_index:
            logger.info(f"  - Bundle ID index: {len(bundle_id_index)} mappings")

        # Initialize TLS passthrough for certificate-pinned hosts
        passthrough_cache = output_dir / "pinned_hosts.json"
        self._tls_passthrough = TLSPassthrough(persist_path=passthrough_cache)
        self._tls_passthrough.set_process_resolver(self._process_resolver)

        # Enable system proxy (development convenience)
        _set_macos_proxy(enable=True)

        logger.info(f"Output directory: {output_dir}")
        logger.info(
            f"JSONata parsing: {'ENABLED' if JSONATA_AVAILABLE else 'DISABLED (install jsonata-python for advanced parsing)'}"
        )
        logger.info(f"========== OXIMY ADDON READY ==========")
        logger.info(f"Listening for AI traffic...")

    async def request(self, flow: http.HTTPFlow) -> None:
        """Classify incoming requests and capture client process info."""
        if not self._enabled or not self._matcher:
            return

        try:
            # Capture client process info FIRST, before matching
            # This must happen as early as possible to avoid race conditions
            # where the client process exits before we can query it
            # Also needed for app matching which requires process info
            client_process: ClientProcess | None = None
            if self._process_resolver:
                try:
                    client_port = flow.client_conn.peername[1]
                    client_process = await self._process_resolver.get_process_for_port(
                        client_port
                    )
                    flow.metadata[OXIMY_CLIENT_KEY] = client_process
                except Exception as e:
                    logger.debug(f"Could not resolve client process: {e}")

            # Match the flow (with client_process for app matching)
            match_result = self._matcher.match(flow, client_process)

            # Store result in flow metadata
            flow.metadata[OXIMY_METADATA_KEY] = match_result

            if match_result.classification != "drop":
                if client_process:
                    logger.debug(
                        f"Client process: {client_process.name} (PID {client_process.pid})"
                    )
                logger.debug(
                    f"Matched: {flow.request.pretty_host} -> "
                    f"{match_result.classification} ({match_result.source_type}/{match_result.source_id})"
                )
        except Exception as e:
            logger.error(
                f"Error in request hook for {flow.request.pretty_host}: {e}",
                exc_info=True,
            )

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Set up streaming handler only for actual streaming responses (SSE)."""
        if not self._enabled:
            return

        match_result: MatchResult | None = flow.metadata.get(OXIMY_METADATA_KEY)
        if not match_result or match_result.classification == "drop":
            return

        # Only set up streaming for actual streaming content types
        # For regular JSON responses (like Grok), we parse in response() hook
        if not flow.response:
            return

        content_type = flow.response.headers.get("content-type", "").lower()
        is_streaming = (
            "text/event-stream" in content_type
            or "application/x-ndjson" in content_type
            or "text/plain" in content_type  # Some APIs stream as text/plain
        )

        if not is_streaming:
            # Regular JSON response - will be parsed in response() hook
            logger.debug(
                f"Non-streaming response for {match_result.source_id}: {content_type}"
            )
            return

        # Get parser config based on source type (website or app)
        response_stream_config = None
        if self._bundle and JSONATA_AVAILABLE:
            if match_result.source_type == "website":
                website = self._bundle.websites.get(match_result.source_id or "")
                if website:
                    feature = website.get("features", {}).get(
                        match_result.endpoint or "", {}
                    )
                    parser_config = feature.get("parser", {})
                    response_stream_config = parser_config.get("response", {}).get(
                        "stream"
                    )

            elif match_result.source_type == "app":
                app = self._bundle.apps.get(match_result.source_id or "")
                if app:
                    feature = app.get("features", {}).get(
                        match_result.endpoint or "", {}
                    )
                    parser_config = feature.get("parser", {})
                    response_stream_config = parser_config.get("response", {}).get(
                        "stream"
                    )

        # Set up streaming buffer if we have a config
        if response_stream_config:
            logger.info(
                f"Setting up streaming buffer for {match_result.source_type}/{match_result.source_id}/{match_result.endpoint} (content-type: {content_type})"
            )
            buffer = ConfigurableStreamBuffer(response_stream_config)
            self._configurable_buffers[flow.id] = buffer
            source_id = match_result.source_id  # Capture for closure

            def create_configurable_handler(buf: ConfigurableStreamBuffer, src_id: str):
                def handler(data: bytes) -> bytes:
                    buf.process_chunk(data)
                    return data

                return handler

            flow.response.stream = create_configurable_handler(buffer, source_id)

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
            # Clean up buffers
            self._configurable_buffers.pop(flow.id, None)

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

        # Build source with referer/origin headers
        referer = flow.request.headers.get("referer") or flow.request.headers.get(
            "referrer"
        )
        origin = flow.request.headers.get("origin")

        source = EventSource(
            type=match_result.source_type or "api",
            id=match_result.source_id or "unknown",
            endpoint=match_result.endpoint,
            referer=referer,
            origin=origin,
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
                subscription=Subscription(plan=""),
            )

        # Full trace event
        include_raw = ctx.options.oximy_include_raw

        # Filter out noisy polling/status endpoints that don't contain conversation data
        path = flow.request.path
        if flow.request.method == "GET" and any(
            x in path for x in ["/stream_status", "/status"]
        ):
            return None

        # Check if this is a file download endpoint (ChatGPT DALL-E images, etc.)
        if match_result.endpoint == "file_download" and flow.response.content:
            return self._build_file_download_event(flow, source, timing, client_process)

        # Check if this is a subscription endpoint (ChatGPT plan info)
        if match_result.endpoint == "subscription" and flow.response.content:
            return self._build_subscription_event(
                flow, match_result, source, timing, client_process
            )

        # Check if we have a configurable parser for this website
        configurable_buffer = self._configurable_buffers.get(flow.id)
        request_data = None
        response_data = None

        # Use configurable parsing for websites (JSONata-based approach)
        logger.info(
            f"_build_event: source_type={match_result.source_type}, source_id={match_result.source_id}, endpoint={match_result.endpoint}"
        )
        logger.info(
            f"_build_event: JSONATA_AVAILABLE={JSONATA_AVAILABLE}, has_bundle={self._bundle is not None}"
        )

        if match_result.source_type == "website" and self._bundle and JSONATA_AVAILABLE:
            website = self._bundle.websites.get(match_result.source_id or "")
            logger.info(f"_build_event: website found={website is not None}")
            if website:
                feature = website.get("features", {}).get(
                    match_result.endpoint or "", {}
                )
                parser_config = feature.get("parser", {})
                request_config = parser_config.get("request")
                logger.info(
                    f"_build_event: feature found={feature is not None}, parser_config keys={list(parser_config.keys())}"
                )

                # Parse request with configurable parser
                # Don't include raw for configurable parsers - we extract what we need
                # and raw would include redundant data (like full chat_history)
                if (
                    request_config
                    and self._configurable_request_parser
                    and flow.request.content
                ):
                    request_data = self._configurable_request_parser.parse(
                        flow.request.content,
                        request_config,
                        include_raw=False,
                    )
                    logger.info(
                        f"Configurable request parsing for {match_result.source_id}: messages={request_data.messages is not None}"
                    )

                # Parse response - either from streaming buffer or direct response body
                response_stream_config = parser_config.get("response", {}).get("stream")
                logger.info(
                    f"_build_event: response_stream_config={response_stream_config is not None}, format={response_stream_config.get('format') if response_stream_config else None}"
                )

                if response_stream_config:
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    from mitmproxy.addons.oximy.parser import (
                        ConfigurableStreamBuffer as CSB,
                    )

                    logger.info(
                        f"_build_event: configurable_buffer in dict={flow.id in self._configurable_buffers}, has_response_content={flow.response and flow.response.content is not None}"
                    )

                    if configurable_buffer:
                        # Streaming response - finalize the buffer
                        logger.info(
                            f"_build_event: Using streaming buffer for {match_result.source_id}"
                        )
                        result = configurable_buffer.finalize()
                        logger.info(
                            f"Streaming buffer finalized for {match_result.source_id}: content_len={len(result.get('content') or '')}"
                        )
                    elif flow.response and flow.response.content:
                        # Non-streaming response - parse the body directly
                        logger.info(
                            f"Parsing response body for {match_result.source_id} ({len(flow.response.content)} bytes)"
                        )
                        logger.info(
                            f"_build_event: response body first 200 bytes: {flow.response.content[:200]}"
                        )
                        buffer = CSB(response_stream_config)
                        buffer.process_chunk(flow.response.content)
                        result = buffer.finalize()
                        logger.info(
                            f"_build_event: buffer.finalize() returned: {list(result.keys())}"
                        )
                    else:
                        logger.info(f"_build_event: No response content available")
                        result = {}

                    response_data = InteractionResponse(
                        content=result.get("content"),
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        usage=result.get("usage"),
                        raw=None,
                    )
                    logger.info(
                        f"Response parsing for {match_result.source_id}: content_len={len(result.get('content') or '')}, model={result.get('model')}"
                    )

        # For websites without parser config, log warning
        if match_result.source_type == "website" and (
            request_data is None or response_data is None
        ):
            logger.warning(
                f"Website {match_result.source_id}/{match_result.endpoint} has no parser config. "
                f"Add configuration to websites.json"
            )
            return None

        # Use configurable parsing for apps (JSONata-based, same as websites)
        if match_result.source_type == "app" and self._bundle and JSONATA_AVAILABLE:
            app = self._bundle.apps.get(match_result.source_id or "")
            logger.info(f"_build_event: app found={app is not None}")
            if app:
                feature = app.get("features", {}).get(match_result.endpoint or "", {})
                parser_config = feature.get("parser", {})
                request_config = parser_config.get("request")
                logger.info(
                    f"_build_event: app feature found={feature is not None}, parser_config keys={list(parser_config.keys())}"
                )

                # Parse request with configurable parser
                # Don't include raw for configurable parsers - we extract what we need
                # and raw would include redundant data (like full chat_history)
                if (
                    request_config
                    and self._configurable_request_parser
                    and flow.request.content
                ):
                    request_data = self._configurable_request_parser.parse(
                        flow.request.content,
                        request_config,
                        include_raw=False,
                    )
                    logger.info(
                        f"Configurable request parsing for app {match_result.source_id}: messages={request_data.messages is not None}"
                    )

                # Parse response - either from streaming buffer or direct response body
                response_stream_config = parser_config.get("response", {}).get("stream")
                logger.info(
                    f"_build_event: app response_stream_config={response_stream_config is not None}"
                )

                if response_stream_config:
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    from mitmproxy.addons.oximy.parser import (
                        ConfigurableStreamBuffer as CSB,
                    )

                    if configurable_buffer:
                        # Streaming response - finalize the buffer
                        logger.info(
                            f"_build_event: Using streaming buffer for app {match_result.source_id}"
                        )
                        result = configurable_buffer.finalize()
                        logger.info(
                            f"Streaming buffer finalized for app {match_result.source_id}: content_len={len(result.get('content') or '')}"
                        )
                    elif flow.response and flow.response.content:
                        # Non-streaming response - parse the body directly
                        logger.info(
                            f"Parsing response body for app {match_result.source_id} ({len(flow.response.content)} bytes)"
                        )
                        buffer = CSB(response_stream_config)
                        buffer.process_chunk(flow.response.content)
                        result = buffer.finalize()
                    else:
                        result = {}

                    response_data = InteractionResponse(
                        content=result.get("content"),
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        usage=result.get("usage"),
                        raw=None,
                    )
                    logger.info(
                        f"Response parsing for app {match_result.source_id}: content_len={len(result.get('content') or '')}, model={result.get('model')}"
                    )

        # For apps without parser config, log warning
        if match_result.source_type == "app" and (
            request_data is None or response_data is None
        ):
            logger.warning(
                f"App {match_result.source_id}/{match_result.endpoint} has no parser config. "
                f"Add configuration to apps.json"
            )
            return None

        # For API providers, use the legacy parsers (still needed for non-website traffic)
        if match_result.source_type == "api":
            if request_data is None and self._request_parser and flow.request.content:
                request_data = self._request_parser.parse(
                    flow.request.content,
                    match_result.api_format,
                    include_raw=include_raw,
                )
            if (
                response_data is None
                and self._response_parser
                and flow.response.content
            ):
                response_data = self._response_parser.parse(
                    flow.response.content,
                    match_result.api_format,
                    include_raw=include_raw,
                )

        if not request_data or not response_data:
            # Can't build full interaction - drop silently
            return None

        # Check if interaction has meaningful content (not empty request/response)
        has_request_content = (
            request_data.prompt
            or request_data.messages
            or request_data.model
            or request_data.raw
        )
        has_response_content = (
            response_data.content or response_data.model or response_data.raw
        )
        if not has_request_content and not has_response_content:
            # Empty interaction - drop silently
            return None

        # Determine model (prefer response, fall back to request)
        model = response_data.model or (request_data.model if request_data else None)

        # Extract rich content analysis from response
        if response_data.content:
            try:
                analysis = analyze_content(response_data.content)
                # Only include if there's interesting content to report
                if (
                    analysis.get("code_blocks")
                    or analysis.get("hyperlinks")
                    or analysis.get("tables")
                    or analysis.get("entities")
                    or analysis.get("citations")
                    or analysis.get("lists")
                ):
                    response_data.content_analysis = analysis
            except Exception as e:
                logger.debug(f"Content analysis failed: {e}")

        interaction = Interaction(
            type=match_result.endpoint or "chat",
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
            subscription=Subscription(plan=""),
        )

    def _build_file_download_event(
        self,
        flow: http.HTTPFlow,
        source: EventSource,
        timing: EventTiming,
        client_process: ClientProcess | None,
    ) -> OximyEvent | None:
        """Build an event for file download endpoints (DALL-E images, etc.)."""
        import json

        path = flow.request.path

        # Extract file_id from the path: /backend-api/files/download/file_xxx
        file_id = None
        if "/files/download/" in path:
            parts = path.split("/files/download/")
            if len(parts) > 1:
                file_id = parts[1].split("?")[0]

        # Parse the JSON response
        try:
            response_json = json.loads(flow.response.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_json = {}

        metadata = {
            "file_id": file_id,
            "download_url": response_json.get("download_url"),
            "file_name": response_json.get("file_name"),
            "file_size_bytes": response_json.get("file_size_bytes"),
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        logger.info(
            f"File download: file_id={file_id}, url={metadata.get('download_url', 'N/A')[:80] if metadata.get('download_url') else 'N/A'}"
        )

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
            client=client_process,
            metadata=metadata,
            subscription=Subscription(plan=""),
        )

    def _build_subscription_event(
        self,
        flow: http.HTTPFlow,
        match_result: MatchResult,
        source: EventSource,
        timing: EventTiming,
        client_process: ClientProcess | None,
    ) -> OximyEvent | None:
        """Build an event for subscription endpoints (user plan info)."""
        import json
        from urllib.parse import parse_qs
        from urllib.parse import urlparse

        # Extract account_id from query params: ?account_id=xxx
        parsed = urlparse(flow.request.path)
        query_params = parse_qs(parsed.query)
        account_id = query_params.get("account_id", [None])[0]

        # Parse the JSON response
        try:
            response_json = json.loads(flow.response.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_json = {}

        # Build metadata with subscription info
        metadata = {
            "request_method": flow.request.method,
            "request_path": flow.request.path,
            "response_status": flow.response.status_code,
            "account_id": account_id,
            "subscription_id": response_json.get("id"),
            "plan_type": response_json.get("plan_type"),
            "billing_period": response_json.get("billing_period"),
            "will_renew": response_json.get("will_renew"),
            "active_start": response_json.get("active_start"),
            "active_until": response_json.get("active_until"),
            "seats_in_use": response_json.get("seats_in_use"),
            "seats_entitled": response_json.get("seats_entitled"),
        }

        # Remove None values for cleaner output
        metadata = {k: v for k, v in metadata.items() if v is not None}

        logger.info(
            f"Subscription captured: account_id={account_id}, plan_type={response_json.get('plan_type')}"
        )

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
            client=client_process,
            metadata=metadata,
            subscription=Subscription(plan=response_json.get("plan_type", "")),
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

    def _build_bundle_id_index(self) -> dict[str, str]:
        """Build a reverse index from bundle_id -> app_id from the registry.

        Apps include both native apps and browsers (category: browser).
        """
        index: dict[str, str] = {}
        if not self._bundle:
            return index

        for app_id, app in self._bundle.apps.items():
            signatures = app.get("signatures", {})
            macos_sig = signatures.get("macos", {})
            if bundle_id := macos_sig.get("bundle_id"):
                index[bundle_id] = app_id

        return index

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
        self._configurable_buffers.clear()
        self._matcher = None
        self._request_parser = None
        self._response_parser = None
        self._bundle = None


# For use with `mitmdump -s .../oximy/addon.py`
addons = [OximyAddon()]
