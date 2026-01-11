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

from mitmproxy import ctx, http

from mitmproxy.addons.oximy.bundle import BundleLoader, DEFAULT_BUNDLE_URL
from mitmproxy.addons.oximy.matcher import TrafficMatcher
from mitmproxy.addons.oximy.parser import (
    RequestParser,
    ResponseParser,
    ConfigurableStreamBuffer,
    ConfigurableRequestParser,
    JSONATA_AVAILABLE,
    analyze_content,
)
from mitmproxy.addons.oximy.passthrough import TLSPassthrough
from mitmproxy.addons.oximy.process import ClientProcess, ProcessResolver
from mitmproxy.addons.oximy.sse import (
    SSEBuffer,
    GeminiBuffer,
    GrokBuffer,
    is_sse_response,
    is_gemini_streaming_response,
    is_grok_streaming_response,
    create_sse_stream_handler,
    create_gemini_stream_handler,
    create_grok_stream_handler,
)
from mitmproxy.addons.oximy.models import (
    EventSource,
    EventTiming,
    Interaction,
    MatchResult,
    OximyEvent,
)
from mitmproxy.addons.oximy.writer import EventWriter

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.bundle import OISPBundle

logger = logging.getLogger(__name__)


class _SuppressDisconnectFilter(logging.Filter):
    """Filter out noisy 'client disconnect' and 'server disconnect' messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Suppress generic disconnect messages (but keep TLS failure messages)
        if msg == "client disconnect" or msg.startswith("server disconnect ") or msg.startswith("client connect") or msg.startswith("server connect"):
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
OXIMY_AUTO_PROXY_ENABLED = True  # Set to False for production
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
                ["networksetup", "-setsecurewebproxy", OXIMY_NETWORK_SERVICE,
                 OXIMY_PROXY_HOST, OXIMY_PROXY_PORT],
                check=True,
                capture_output=True,
            )
            # Enable HTTP proxy
            subprocess.run(
                ["networksetup", "-setwebproxy", OXIMY_NETWORK_SERVICE,
                 OXIMY_PROXY_HOST, OXIMY_PROXY_PORT],
                check=True,
                capture_output=True,
            )
            logger.info(f"System proxy enabled: {OXIMY_PROXY_HOST}:{OXIMY_PROXY_PORT}")
        else:
            # Disable HTTPS proxy
            subprocess.run(
                ["networksetup", "-setsecurewebproxystate", OXIMY_NETWORK_SERVICE, "off"],
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
        logger.warning(f"Failed to {'enable' if enable else 'disable'} system proxy: {e}")
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

        # Initialize bundle loader
        self._bundle_loader = BundleLoader(
            bundle_url=ctx.options.oximy_bundle_url,
            max_age_hours=ctx.options.oximy_bundle_refresh_hours,
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

        # Initialize TLS passthrough for certificate-pinned hosts
        passthrough_cache = output_dir / "pinned_hosts.json"
        self._tls_passthrough = TLSPassthrough(persist_path=passthrough_cache)
        self._tls_passthrough.set_process_resolver(self._process_resolver)

        # Enable system proxy (development convenience)
        _set_macos_proxy(enable=True)

        logger.info(f"Oximy addon enabled, writing to {output_dir}")

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
        """Set up SSE or Gemini streaming if needed."""
        if not self._enabled:
            return

        match_result: MatchResult | None = flow.metadata.get(OXIMY_METADATA_KEY)
        if not match_result or match_result.classification == "drop":
            return

        # Check if this is a website with configurable parser
        if match_result.source_type == "website" and self._bundle and JSONATA_AVAILABLE:
            website = self._bundle.websites.get(match_result.source_id or "")
            logger.debug(f"Looking up website '{match_result.source_id}': found={website is not None}")

            if website:
                feature = website.get("features", {}).get(match_result.endpoint or "", {})
                parser_config = feature.get("parser", {})
                response_stream_config = parser_config.get("response", {}).get("stream")

                logger.debug(
                    f"Website {match_result.source_id}: endpoint={match_result.endpoint}, "
                    f"feature_found={bool(feature)}, parser_found={bool(parser_config)}, "
                    f"stream_config_found={bool(response_stream_config)}"
                )

                if response_stream_config and flow.response:
                    logger.info(f"Setting up ConfigurableStreamBuffer for {match_result.source_id}/{match_result.endpoint}")
                    buffer = ConfigurableStreamBuffer(response_stream_config)
                    self._configurable_buffers[flow.id] = buffer

                    # Create stream handler that passes through while accumulating
                    # mitmproxy calls this with each data chunk as bytes
                    def create_configurable_handler(buf: ConfigurableStreamBuffer):
                        def handler(data: bytes) -> bytes:
                            buf.process_chunk(data)
                            return data
                        return handler

                    flow.response.stream = create_configurable_handler(buffer)
                    return
                elif not response_stream_config:
                    logger.warning(
                        f"No stream config in parser for {match_result.source_id}/{match_result.endpoint}. "
                        f"parser_config keys: {list(parser_config.keys())}"
                    )
            else:
                logger.warning(
                    f"Website '{match_result.source_id}' not found in bundle. "
                    f"Available websites: {list(self._bundle.websites.keys())}"
                )
        elif match_result.source_type == "website":
            if not JSONATA_AVAILABLE:
                logger.error("JSONata not available - cannot use data-driven parsing")
            elif not self._bundle:
                logger.error("Bundle not loaded - cannot look up website config")

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
            if event.client.parent_name and event.client.parent_name != event.client.name:
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

    def _build_event(self, flow: http.HTTPFlow, match_result: MatchResult) -> OximyEvent | None:
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

        # Filter out noisy polling/status endpoints that don't contain conversation data
        path = flow.request.path
        if flow.request.method == "GET" and any(x in path for x in ["/stream_status", "/status"]):
            return None

        # Check if this is a file download endpoint (ChatGPT DALL-E images, etc.)
        if match_result.endpoint == "file_download" and flow.response.content:
            return self._build_file_download_event(flow, source, timing, client_process)

        # Check if this is a subscription endpoint (ChatGPT plan info)
        if match_result.endpoint == "subscription" and flow.response.content:
            return self._build_subscription_event(flow, match_result, source, timing, client_process)

        # Check if we have a configurable parser for this website
        configurable_buffer = self._configurable_buffers.get(flow.id)
        request_data = None
        if is_grok and flow.request.content:
            # Grok has message in JSON body
            grok_req = parse_grok_request(flow.request.content)
            from mitmproxy.addons.oximy.models import InteractionRequest
            request_data = InteractionRequest(
                messages=[{"role": "user", "content": grok_req.get("prompt")}] if grok_req.get("prompt") else None,
                model=grok_req.get("model"),
                raw=grok_req if include_raw else None,
            )
        elif is_perplexity and flow.request.content:
            # Perplexity has query_str in JSON body
            perplexity_req = parse_perplexity_request(flow.request.content)
            from mitmproxy.addons.oximy.models import InteractionRequest
            request_data = InteractionRequest(
                messages=[{"role": "user", "content": perplexity_req.get("prompt")}] if perplexity_req.get("prompt") else None,
                model=perplexity_req.get("model"),
                raw=perplexity_req if include_raw else None,
            )
        elif is_deepseek and flow.request.content:
            # DeepSeek has prompt directly in JSON body
            deepseek_req = parse_deepseek_request(flow.request.content)
            from mitmproxy.addons.oximy.models import InteractionRequest
            request_data = InteractionRequest(
                messages=[{"role": "user", "content": deepseek_req.get("prompt")}] if deepseek_req.get("prompt") else None,
                model=None,
                raw=deepseek_req if include_raw else None,
            )
        elif is_gemini and flow.request.content:
            # Use Gemini-specific parser
            gemini_req = parse_gemini_request(flow.request.content)
            from mitmproxy.addons.oximy.models import InteractionRequest
            request_data = InteractionRequest(
                messages=[{"role": "user", "content": gemini_req.get("prompt")}] if gemini_req.get("prompt") else None,
                model=None,  # Gemini doesn't expose model in request
                raw={"prompt": gemini_req.get("prompt"), "conversation_id": gemini_req.get("conversation_id")} if include_raw else None,
            )
        elif self._request_parser and flow.request.content:
            request_data = self._request_parser.parse(
                flow.request.content,
                match_result.api_format,
                include_raw=include_raw,
            )
        response_data = None

        # Try configurable parsing first (new JSONata-based approach)
        if match_result.source_type == "website" and self._bundle and JSONATA_AVAILABLE:
            website = self._bundle.websites.get(match_result.source_id or "")
            if website:
                feature = website.get("features", {}).get(match_result.endpoint or "", {})
                parser_config = feature.get("parser", {})
                request_config = parser_config.get("request")
                response_config = parser_config.get("response")

                # Parse request with configurable parser
                if request_config and self._configurable_request_parser and flow.request.content:
                    request_data = self._configurable_request_parser.parse(
                        flow.request.content,
                        request_config,
                        include_raw=include_raw,
                    )
                    logger.info(f"Configurable request parsing for {match_result.source_id}: messages={request_data.messages is not None}")

                # Handle streaming and other API-specific response accumulation
                if is_gemini and gemini_buffer:
                    # Use accumulated Gemini streaming data
                    logger.info(f"Gemini buffer has {len(gemini_buffer.accumulated_bytes)} bytes")
                    gemini_resp = gemini_buffer.finalize()
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    response_data = InteractionResponse(
                        content=gemini_resp.get("content"),
                        model="gemini",
                        finish_reason=None,
                        usage=None,
                        raw=None,  # Don't include raw for Gemini (too large)
                    )
                    logger.info(f"Gemini response content: {gemini_resp.get('content')[:100] if gemini_resp.get('content') else 'None'}")
                elif is_gemini and flow.response and flow.response.content:
                    # Fallback: try parsing flow.response.content directly (non-streaming)
                    logger.info(f"Gemini fallback: no buffer, using flow.response.content ({len(flow.response.content)} bytes)")
                    gemini_resp = parse_gemini_response(flow.response.content)
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    response_data = InteractionResponse(
                        content=gemini_resp.get("content"),
                        model="gemini",
                        finish_reason=None,
                        usage=None,
                        raw=None,  # Don't include raw for Gemini (too large)
                    )
                elif is_gemini:
                    # Gemini but no buffer and no content
                    logger.warning(f"Gemini: no buffer and no response content (flow.response.content length: {len(flow.response.content or b'')})")
                elif is_grok and grok_buffer:
                    # Use accumulated Grok streaming data
                    logger.info(f"Grok: Using buffer with {len(grok_buffer.accumulated_bytes)} bytes")
                    grok_resp = grok_buffer.finalize()
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    response_data = InteractionResponse(
                        content=grok_resp.get("content"),
                        model=grok_resp.get("model"),
                        finish_reason=None,
                        usage=None,
                        raw=None,  # Don't include raw for Grok streaming (too large)
                    )
                    logger.info(f"Grok response_data content: {grok_resp.get('content')[:100] if grok_resp.get('content') else 'None'}")
                elif is_grok and flow.response and flow.response.content:
                    # Fallback: try parsing flow.response.content directly (non-streaming)
                    logger.info(f"Grok: NO BUFFER, using flow.response.content ({len(flow.response.content)} bytes)")
                    grok_resp = parse_grok_response(flow.response.content)
                    from mitmproxy.addons.oximy.models import InteractionResponse
                    response_data = InteractionResponse(
                        content=grok_resp.get("content"),
                        model=grok_resp.get("model"),
                        finish_reason=None,
                        usage=None,
                        raw=None,  # Don't include raw for Grok streaming (too large)
                    )
                    logger.info(f"Grok fallback response_data content: {grok_resp.get('content')[:100] if grok_resp.get('content') else 'None'}")
                elif is_grok:
                    # Grok but no buffer and no content
                    logger.warning(f"Grok: no buffer and no response content (flow.response.content length: {len(flow.response.content or b'')})")
                elif sse_buffer:
                    # Use accumulated SSE data
                    sse_result = sse_buffer.finalize()
                    from mitmproxy.addons.oximy.models import InteractionResponse

                # Parse response from configurable buffer
                if configurable_buffer:
                    from mitmproxy.addons.oximy.types import InteractionResponse
                    result = configurable_buffer.finalize()
                    response_data = InteractionResponse(
                        content=result.get("content"),
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        usage=result.get("usage"),
                        raw=None,  # Don't include raw for streaming (too large)
                    )
                    logger.info(f"Configurable response parsing for {match_result.source_id}: content_len={len(result.get('content') or '')}")

        # For websites without parser config, log warning
        if match_result.source_type == "website" and (request_data is None or response_data is None):
            logger.warning(
                f"Website {match_result.source_id}/{match_result.endpoint} has no parser config. "
                f"Add configuration to websites.json"
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
            if response_data is None and self._response_parser and flow.response.content:
                response_data = self._response_parser.parse(
                    flow.response.content,
                    match_result.api_format,
                    include_raw=include_raw,
                )

        if not request_data or not response_data:
            # Can't build full interaction - drop silently
            return None

        # Check if interaction has meaningful content (not empty request/response)
        has_request_content = request_data.messages or request_data.model or request_data.raw
        has_response_content = response_data.content or response_data.model or response_data.raw
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
                if (analysis.get("code_blocks") or analysis.get("hyperlinks") or
                    analysis.get("tables") or analysis.get("entities") or
                    analysis.get("citations") or analysis.get("lists")):
                    response_data.content_analysis = analysis
            except Exception as e:
                logger.debug(f"Content analysis failed: {e}")

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

        logger.info(f"File download: file_id={file_id}, url={metadata.get('download_url', 'N/A')[:80] if metadata.get('download_url') else 'N/A'}")

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
            client=client_process,
            metadata=metadata,
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
        from urllib.parse import parse_qs, urlparse

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

        logger.info(f"Subscription captured: account_id={account_id}, plan_type={response_json.get('plan_type')}")

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
            client=client_process,
            metadata=metadata,
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
                    (flow.response.timestamp_start - flow.request.timestamp_start) * 1000
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
        self._configurable_buffers.clear()
        self._matcher = None
        self._request_parser = None
        self._response_parser = None
        self._bundle = None


# For use with `mitmdump -s .../oximy/addon.py`
addons = [OximyAddon()]
