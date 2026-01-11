"""
Investigation Mode addon for mitmproxy.

Captures raw traffic for analysis and debugging. Unlike the production
OximyAddon which normalizes data, this preserves:
- Raw request/response bodies
- Individual SSE chunks with timing
- Parse attempts and errors
- Full headers

Usage:
    mitmdump -s investigator.py --set investigate_enabled=true

Filter by domain:
    --set investigate_domains="chatgpt.com,api.openai.com"

Filter by app:
    --set investigate_apps="Cursor,Granola,Slack"

All traffic (no filtering):
    --set investigate_capture_all=true
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import IO

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.addons.oximy.investigator_types import InvestigationEvent
from mitmproxy.addons.oximy.investigator_types import InvestigationSession
from mitmproxy.addons.oximy.investigator_types import MatchAttempt
from mitmproxy.addons.oximy.investigator_types import ParseAttempt
from mitmproxy.addons.oximy.investigator_types import SSEChunk
from mitmproxy.addons.oximy.process import ClientProcess
from mitmproxy.addons.oximy.process import ProcessResolver

logger = logging.getLogger(__name__)

# Metadata keys
INVESTIGATE_CLIENT_KEY = "investigate_client"
INVESTIGATE_SSE_KEY = "investigate_sse"
INVESTIGATE_START_TIME_KEY = "investigate_start_time"

# Limits
MAX_BODY_SIZE = 1024 * 1024  # 1MB max body to store
MAX_SSE_CHUNKS = 10000  # Max SSE chunks to store per response


class InvestigationSSEBuffer:
    """
    SSE buffer that preserves individual chunks with timing.

    Unlike the production SSEBuffer which reconstructs content,
    this keeps every chunk for debugging.
    """

    def __init__(self):
        self.chunks: list[SSEChunk] = []
        self.reconstructed_content: str = ""
        self._buffer: str = ""
        self._last_chunk_time: float = time.time()
        self._start_time: float = time.time()
        self._chunk_index: int = 0

    def process_chunk(self, chunk: bytes) -> bytes:
        """Process an SSE chunk while preserving timing data."""
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return chunk

        current_time = time.time()
        self._buffer += text

        # Process complete SSE events
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            self._process_event(event, current_time, len(chunk))

        self._last_chunk_time = current_time
        return chunk

    def _process_event(self, event: str, timestamp: float, size_bytes: int) -> None:
        """Process a single SSE event and store it."""
        if self._chunk_index >= MAX_SSE_CHUNKS:
            return  # Stop storing after limit

        lines = event.strip().split("\n")
        event_type: str | None = None
        data_parts: list[str] = []

        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_parts.append(line[6:])
            elif line.startswith("data:"):
                data_parts.append(line[5:])

        if not data_parts:
            return

        data_raw = "\n".join(data_parts)

        # Skip stream end markers
        if data_raw.strip() in ("[DONE]", ""):
            return

        # Attempt JSON parse
        data_parsed: dict[str, Any] | None = None
        try:
            data_parsed = json.loads(data_raw)
        except json.JSONDecodeError:
            pass

        # Calculate delta from last chunk
        delta_ms = int((timestamp - self._last_chunk_time) * 1000)

        # Create chunk record
        chunk = SSEChunk(
            index=self._chunk_index,
            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            event_type=event_type,
            data_raw=data_raw[:10000],  # Truncate very long data
            data_parsed=data_parsed,
            delta_ms=delta_ms,
            size_bytes=size_bytes,
        )
        self.chunks.append(chunk)
        self._chunk_index += 1

        # Also try to reconstruct content (best effort)
        self._accumulate_content(data_parsed or data_raw)

    def _accumulate_content(self, data: dict[str, Any] | str) -> None:
        """Best-effort content reconstruction."""
        if isinstance(data, str):
            return

        # Try various SSE content formats

        # ChatGPT web: {"v": "text"}
        if "v" in data and "o" not in data and "p" not in data:
            value = data.get("v")
            if isinstance(value, str):
                self.reconstructed_content += value
                return

        # ChatGPT web: {"o": "append", "v": "text", "p": "..."}
        if data.get("o") == "append" and "v" in data:
            value = data.get("v")
            if isinstance(value, str):
                self.reconstructed_content += value
                return

        # OpenAI: choices[0].delta.content
        choices = data.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                self.reconstructed_content += content
                return

        # Anthropic: delta.text
        delta = data.get("delta", {})
        if "text" in delta:
            self.reconstructed_content += delta["text"]
            return

        # Anthropic content_block_delta
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            text = delta.get("text")
            if text:
                self.reconstructed_content += text

    def finalize(self) -> tuple[list[SSEChunk], str]:
        """Return accumulated chunks and reconstructed content."""
        # Process any remaining buffer
        if self._buffer.strip():
            self._process_event(self._buffer, time.time(), len(self._buffer))
            self._buffer = ""

        return self.chunks, self.reconstructed_content


class InvestigationWriter:
    """
    Writes investigation events to JSONL files.

    Similar to EventWriter but for investigation sessions.
    """

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self._fo: IO[bytes] | None = None
        self._event_count: int = 0

    def open(self) -> None:
        """Open the output file."""
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._fo = open(self.output_path, "ab")
            logger.info(f"Investigation output: {self.output_path}")
        except IOError as e:
            logger.error(f"Failed to open investigation file: {e}")

    def write_session(self, session: InvestigationSession) -> None:
        """Write session metadata."""
        self._write_line(session.to_dict())

    def write_event(self, event: InvestigationEvent) -> None:
        """Write an investigation event."""
        self._write_line(event.to_dict())
        self._event_count += 1

        if self._event_count % 10 == 0:
            logger.debug(f"Investigation: {self._event_count} events captured")

    def _write_line(self, data: dict[str, Any]) -> None:
        """Write a single JSON line."""
        if self._fo is None:
            return

        try:
            line = json.dumps(data, separators=(",", ":"), default=str)
            self._fo.write((line + "\n").encode("utf-8"))
            self._fo.flush()
        except (IOError, OSError) as e:
            logger.error(f"Failed to write investigation event: {e}")

    def close(self) -> None:
        """Close the output file."""
        if self._fo is not None:
            try:
                self._fo.flush()
                self._fo.close()
                logger.info(f"Investigation complete: {self._event_count} events")
            except IOError:
                pass
            finally:
                self._fo = None

    @property
    def event_count(self) -> int:
        return self._event_count


class InvestigatorAddon:
    """
    Investigation mode addon for raw traffic capture.

    Captures everything for analysis, unlike the production addon
    which filters and normalizes.
    """

    def __init__(self):
        self._enabled: bool = False
        self._writer: InvestigationWriter | None = None
        self._process_resolver: ProcessResolver | None = None
        self._session: InvestigationSession | None = None
        self._sse_buffers: dict[str, InvestigationSSEBuffer] = {}

        # Filters
        self._domains: set[str] = set()
        self._apps: set[str] = set()
        self._capture_all: bool = False

        # Optional: use production matcher for comparison
        self._matcher = None
        self._request_parser = None
        self._response_parser = None

    def load(self, loader) -> None:
        """Register addon options."""
        loader.add_option(
            name="investigate_enabled",
            typespec=bool,
            default=False,
            help="Enable investigation mode",
        )
        loader.add_option(
            name="investigate_output",
            typespec=str,
            default="",
            help="Output file path (default: ~/.oximy/investigations/session_TIMESTAMP.jsonl)",
        )
        loader.add_option(
            name="investigate_domains",
            typespec=str,
            default="",
            help="Comma-separated domains to capture (e.g., 'chatgpt.com,api.openai.com')",
        )
        loader.add_option(
            name="investigate_apps",
            typespec=str,
            default="",
            help="Comma-separated app names to capture (e.g., 'Cursor,Granola,Slack')",
        )
        loader.add_option(
            name="investigate_capture_all",
            typespec=bool,
            default=False,
            help="Capture all traffic (ignore domain/app filters)",
        )
        loader.add_option(
            name="investigate_description",
            typespec=str,
            default="",
            help="Description for this investigation session",
        )
        loader.add_option(
            name="investigate_include_matcher",
            typespec=bool,
            default=True,
            help="Include production matcher results for comparison",
        )

    def configure(self, updated: set[str]) -> None:
        """Handle configuration changes."""
        relevant = {
            "investigate_enabled",
            "investigate_output",
            "investigate_domains",
            "investigate_apps",
            "investigate_capture_all",
        }
        if not relevant.intersection(updated):
            return

        new_enabled = ctx.options.investigate_enabled

        if not new_enabled:
            if self._enabled:
                logger.info("Investigation mode disabled")
                self._cleanup()
            self._enabled = False
            return

        self._enabled = True

        # Parse filters
        domains_str = ctx.options.investigate_domains.strip()
        self._domains = set(
            d.strip().lower() for d in domains_str.split(",") if d.strip()
        )

        apps_str = ctx.options.investigate_apps.strip()
        self._apps = set(a.strip() for a in apps_str.split(",") if a.strip())

        self._capture_all = ctx.options.investigate_capture_all

        # Validate filters
        if not self._capture_all and not self._domains and not self._apps:
            logger.warning(
                "Investigation mode: No filters set. Use --set investigate_capture_all=true "
                "or specify domains/apps to capture."
            )
            # Don't disable, but warn

        # Setup output
        output_str = ctx.options.investigate_output.strip()
        if output_str:
            output_path = Path(output_str).expanduser()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                Path.home() / ".oximy" / "investigations" / f"session_{timestamp}.jsonl"
            )

        self._writer = InvestigationWriter(output_path)
        self._writer.open()

        # Initialize process resolver
        self._process_resolver = ProcessResolver()

        # Create session
        self._session = InvestigationSession.create(
            description=ctx.options.investigate_description or None,
            filters={
                "domains": list(self._domains),
                "apps": list(self._apps),
                "capture_all": self._capture_all,
            },
        )
        self._writer.write_session(self._session)

        # Optionally load production matcher for comparison
        if ctx.options.investigate_include_matcher:
            self._init_production_matcher()

        # Log startup
        filter_desc = []
        if self._capture_all:
            filter_desc.append("ALL traffic")
        else:
            if self._domains:
                filter_desc.append(f"domains: {', '.join(sorted(self._domains))}")
            if self._apps:
                filter_desc.append(f"apps: {', '.join(sorted(self._apps))}")

        logger.info(
            f"Investigation mode enabled: {' | '.join(filter_desc) or 'no filters'}"
        )
        logger.info(f"Output: {output_path}")

    def _init_production_matcher(self) -> None:
        """Initialize production matcher for comparison."""
        try:
            from mitmproxy.addons.oximy.bundle import BundleLoader
            from mitmproxy.addons.oximy.matcher import TrafficMatcher
            from mitmproxy.addons.oximy.parser import RequestParser
            from mitmproxy.addons.oximy.parser import ResponseParser

            loader = BundleLoader()
            bundle = loader.load()
            self._matcher = TrafficMatcher(bundle)
            self._request_parser = RequestParser(bundle.parsers)
            self._response_parser = ResponseParser(bundle.parsers)
            logger.debug("Production matcher loaded for comparison")
        except Exception as e:
            logger.warning(f"Could not load production matcher: {e}")

    def request(self, flow: http.HTTPFlow) -> None:
        """Capture client process info immediately on request."""
        if not self._enabled:
            return

        # Record start time
        flow.metadata[INVESTIGATE_START_TIME_KEY] = time.time()

        # Check if we should capture this request
        if not self._should_capture(flow, client_process=None):
            return

        # Capture client process info IMMEDIATELY
        if self._process_resolver:
            try:
                client_port = flow.client_conn.peername[1]
                client_process = self._process_resolver.get_process_for_port(
                    client_port
                )
                flow.metadata[INVESTIGATE_CLIENT_KEY] = client_process

                # Re-check app filter with actual process info
                if not self._should_capture(flow, client_process):
                    del flow.metadata[INVESTIGATE_CLIENT_KEY]
                    return

                logger.debug(
                    f"Investigating: {flow.request.pretty_host} from {client_process.name}"
                )
            except Exception as e:
                logger.debug(f"Failed to get process info: {e}")

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """Set up SSE streaming capture if needed."""
        if not self._enabled:
            return

        # Only capture if we're tracking this flow
        if INVESTIGATE_CLIENT_KEY not in flow.metadata and not self._capture_all:
            # Re-check in case we should capture based on response
            if not self._should_capture(flow, None):
                return

        if flow.response and self._is_sse_response(flow.response.headers):
            logger.debug(f"SSE detected: {flow.request.pretty_host}{flow.request.path}")
            buffer = InvestigationSSEBuffer()
            self._sse_buffers[flow.id] = buffer
            flow.metadata[INVESTIGATE_SSE_KEY] = True
            flow.response.stream = lambda data: buffer.process_chunk(data)

    def response(self, flow: http.HTTPFlow) -> None:
        """Build and write investigation event."""
        if not self._enabled or not self._writer or not self._session:
            return

        # Check if we should capture
        client_process: ClientProcess | None = flow.metadata.get(INVESTIGATE_CLIENT_KEY)
        if not self._should_capture(flow, client_process):
            return

        try:
            event = self._build_event(flow, client_process)
            if event:
                self._writer.write_event(event)
                self._log_event(event)
        except Exception as e:
            logger.error(f"Failed to build investigation event: {e}", exc_info=True)
        finally:
            self._sse_buffers.pop(flow.id, None)

    def _should_capture(
        self, flow: http.HTTPFlow, client_process: ClientProcess | None
    ) -> bool:
        """Check if this flow should be captured based on filters."""
        if self._capture_all:
            return True

        host = flow.request.pretty_host.lower()

        # Check domain filter
        if self._domains:
            for domain in self._domains:
                if domain in host or host.endswith(domain):
                    return True

        # Check app filter
        if self._apps and client_process:
            app_name = client_process.parent_name or client_process.name
            if app_name:
                for app in self._apps:
                    if app.lower() in app_name.lower():
                        return True

        # No filters matched
        return bool(self._domains) is False and bool(self._apps) is False

    def _is_sse_response(self, headers) -> bool:
        """Check if response is SSE."""
        content_type = headers.get("content-type", "")
        return "text/event-stream" in content_type.lower()

    def _build_event(
        self, flow: http.HTTPFlow, client_process: ClientProcess | None
    ) -> InvestigationEvent | None:
        """Build an investigation event from a flow."""
        if not flow.response or not self._session:
            return None

        # Request body
        req_body_raw: str | None = None
        req_body_parsed: dict[str, Any] | None = None
        req_body_size = len(flow.request.content or b"")
        req_body_truncated = False

        if flow.request.content:
            if req_body_size <= MAX_BODY_SIZE:
                try:
                    req_body_raw = flow.request.content.decode("utf-8")
                    try:
                        req_body_parsed = json.loads(req_body_raw)
                    except json.JSONDecodeError:
                        pass
                except UnicodeDecodeError:
                    req_body_raw = f"<binary: {req_body_size} bytes>"
            else:
                req_body_raw = f"<truncated: {req_body_size} bytes>"
                req_body_truncated = True

        # Response body (for non-SSE)
        resp_body_raw: str | None = None
        resp_body_parsed: dict[str, Any] | None = None
        resp_body_size = len(flow.response.content or b"")
        resp_body_truncated = False

        is_sse = flow.metadata.get(INVESTIGATE_SSE_KEY, False)
        sse_chunks: list[SSEChunk] | None = None
        sse_reconstructed: str | None = None

        if is_sse:
            # Get SSE data
            sse_buffer = self._sse_buffers.get(flow.id)
            if sse_buffer:
                sse_chunks, sse_reconstructed = sse_buffer.finalize()
        else:
            # Regular response
            if flow.response.content:
                if resp_body_size <= MAX_BODY_SIZE:
                    try:
                        resp_body_raw = flow.response.content.decode("utf-8")
                        try:
                            resp_body_parsed = json.loads(resp_body_raw)
                        except json.JSONDecodeError:
                            pass
                    except UnicodeDecodeError:
                        resp_body_raw = f"<binary: {resp_body_size} bytes>"
                else:
                    resp_body_raw = f"<truncated: {resp_body_size} bytes>"
                    resp_body_truncated = True

        # Timing
        duration_ms: int | None = None
        ttfb_ms: int | None = None

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

        # Match attempt (if matcher available)
        match_attempt: MatchAttempt | None = None
        if self._matcher:
            try:
                result = self._matcher.match(flow)
                match_attempt = MatchAttempt(
                    classification=result.classification,
                    source_type=result.source_type,
                    source_id=result.source_id,
                    api_format=result.api_format,
                    endpoint=result.endpoint,
                    match_reason=self._get_match_reason(result),
                )
            except Exception as e:
                match_attempt = MatchAttempt(
                    classification="drop",
                    source_type=None,
                    source_id=None,
                    api_format=None,
                    endpoint=None,
                    match_reason=f"error: {e}",
                )

        # Parse attempt (if parsers available)
        parse_attempt: ParseAttempt | None = None
        if (
            self._request_parser
            and self._response_parser
            and match_attempt
            and match_attempt.api_format
        ):
            parse_attempt = self._try_parse(flow, match_attempt.api_format)

        # Build headers dict
        req_headers = dict(flow.request.headers)
        resp_headers = dict(flow.response.headers)

        return InvestigationEvent.create(
            host=flow.request.pretty_host,
            url=flow.request.url,
            path=flow.request.path,
            method=flow.request.method,
            scheme=flow.request.scheme,
            flow_id=flow.id,
            session_id=self._session.session_id,
            client=client_process,
            request_headers=req_headers,
            request_content_type=flow.request.headers.get("content-type"),
            request_body_raw=req_body_raw,
            request_body_parsed=req_body_parsed,
            request_body_size=req_body_size,
            request_body_truncated=req_body_truncated,
            response_status=flow.response.status_code,
            response_headers=resp_headers,
            response_content_type=flow.response.headers.get("content-type"),
            response_body_raw=resp_body_raw,
            response_body_parsed=resp_body_parsed,
            response_body_size=resp_body_size,
            response_body_truncated=resp_body_truncated,
            is_sse=is_sse,
            sse_chunks=sse_chunks,
            sse_reconstructed_content=sse_reconstructed,
            duration_ms=duration_ms,
            ttfb_ms=ttfb_ms,
            match_attempt=match_attempt,
            parse_attempt=parse_attempt,
        )

    def _get_match_reason(self, result) -> str:
        """Determine why traffic was matched."""
        if result.classification == "drop":
            return "unknown"
        if result.source_type == "website":
            return "website"
        if result.provider_id:
            return "domain_lookup"
        return "domain_pattern"

    def _try_parse(self, flow: http.HTTPFlow, api_format: str) -> ParseAttempt:
        """Attempt to parse request/response with production parsers."""
        errors: list[str] = []
        request_extracted: dict[str, Any] | None = None
        response_extracted: dict[str, Any] | None = None

        if self._request_parser and flow.request.content:
            try:
                result = self._request_parser.parse(
                    flow.request.content, api_format, include_raw=False
                )
                request_extracted = result.to_dict() if result else None
            except Exception as e:
                errors.append(f"Request parse error: {e}")

        if self._response_parser and flow.response and flow.response.content:
            try:
                result = self._response_parser.parse(
                    flow.response.content, api_format, include_raw=False
                )
                response_extracted = result.to_dict() if result else None
            except Exception as e:
                errors.append(f"Response parse error: {e}")

        return ParseAttempt(
            api_format=api_format,
            request_extracted=request_extracted,
            response_extracted=response_extracted,
            errors=errors,
        )

    def _log_event(self, event: InvestigationEvent) -> None:
        """Log a summary of captured event."""
        client_str = ""
        if event.client:
            name = event.client.parent_name or event.client.name
            client_str = f" [{name}]"

        sse_str = " (SSE)" if event.is_sse else ""
        chunks_str = f" {len(event.sse_chunks)} chunks" if event.sse_chunks else ""

        match_str = ""
        if event.match_attempt:
            if event.match_attempt.classification == "drop":
                match_str = " [UNKNOWN]"
            else:
                match_str = f" [{event.match_attempt.source_id or 'matched'}]"

        logger.info(
            f"Captured:{client_str} {event.method} {event.host}{event.path[:40]}"
            f"{'...' if len(event.path) > 40 else ''} -> {event.response_status}"
            f"{sse_str}{chunks_str}{match_str}"
        )

    def done(self) -> None:
        """Clean up on shutdown."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._writer:
            self._writer.close()
            self._writer = None

        if self._process_resolver:
            self._process_resolver.clear_cache()
            self._process_resolver = None

        self._sse_buffers.clear()
        self._session = None


# For use with `mitmdump -s .../investigator.py`
addons = [InvestigatorAddon()]
