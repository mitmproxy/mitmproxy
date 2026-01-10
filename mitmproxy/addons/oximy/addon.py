"""
Main Oximy addon for mitmproxy.

Captures AI API traffic based on OISP bundle whitelists,
normalizes events, and writes to JSONL files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from mitmproxy import ctx, http

from mitmproxy.addons.oximy.bundle import BundleLoader, DEFAULT_BUNDLE_URL
from mitmproxy.addons.oximy.matcher import TrafficMatcher
from mitmproxy.addons.oximy.parser import RequestParser, ResponseParser
from mitmproxy.addons.oximy.sse import SSEBuffer, is_sse_response, create_sse_stream_handler
from mitmproxy.addons.oximy.types import (
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

# Metadata key for storing match result on flows
OXIMY_METADATA_KEY = "oximy_match"


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

        # Initialize writer
        output_dir = Path(ctx.options.oximy_output_dir).expanduser()
        self._writer = EventWriter(output_dir)

        logger.info(f"Oximy addon enabled, writing to {output_dir}")

    def request(self, flow: http.HTTPFlow) -> None:
        """Classify incoming requests."""
        if not self._enabled or not self._matcher:
            return

        # Match the flow
        match_result = self._matcher.match(flow)

        # Store result in flow metadata
        flow.metadata[OXIMY_METADATA_KEY] = match_result

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
        except Exception as e:
            logger.error(f"Failed to process flow: {e}", exc_info=True)
        finally:
            # Clean up SSE buffer
            self._sse_buffers.pop(flow.id, None)

    def _build_event(self, flow: http.HTTPFlow, match_result: MatchResult) -> OximyEvent | None:
        """Build an OximyEvent from a flow."""
        if not flow.response:
            return None

        # Calculate timing
        timing = self._calculate_timing(flow)

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
            from mitmproxy.addons.oximy.types import InteractionResponse

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
            provider=match_result.provider_id,
            request=request_data,
            response=response_data,
        )

        return OximyEvent.create(
            source=source,
            trace_level="full",
            timing=timing,
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
                    (flow.response.timestamp_start - flow.request.timestamp_start) * 1000
                )

        return EventTiming(duration_ms=duration_ms, ttfb_ms=ttfb_ms)

    def done(self) -> None:
        """Clean up on shutdown."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._writer:
            self._writer.close()
            self._writer = None

        self._sse_buffers.clear()
        self._matcher = None
        self._request_parser = None
        self._response_parser = None
        self._bundle = None


# For use with `mitmdump -s .../oximy/addon.py`
addons = [OximyAddon()]
