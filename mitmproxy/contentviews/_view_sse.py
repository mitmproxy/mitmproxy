import json
import re
from typing import Any

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._utils import yaml_dumps

_LINE_SPLIT_RE = re.compile(r"\r\n|\r|\n")


def _try_parse_json(value: str) -> Any:
    stripped = value.strip()
    if stripped.startswith(("{", "[")):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def _build_event(
    event_type: str | None,
    event_id: str | None,
    retry: int | None,
    data_lines: list[str],
) -> dict[str, Any]:
    event: dict[str, Any] = {}
    if event_type is not None:
        event["event"] = event_type
    if event_id is not None:
        event["id"] = event_id
    if retry is not None:
        event["retry"] = retry
    if data_lines:
        event["data"] = _try_parse_json("\n".join(data_lines))
    return event


def parse_sse(data: bytes) -> list[dict[str, Any]]:
    """
    Parse a Server-Sent Events (text/event-stream) payload according to the
    WHATWG Event Stream specification.
    """
    text = data.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]

    events: list[dict[str, Any]] = []
    event_type: str | None = None
    event_id: str | None = None
    retry: int | None = None
    data_lines: list[str] = []

    def flush() -> None:
        nonlocal event_type, event_id, retry, data_lines
        if (
            event_type is not None
            or event_id is not None
            or retry is not None
            or data_lines
        ):
            events.append(_build_event(event_type, event_id, retry, data_lines))
            event_type = None
            event_id = None
            retry = None
            data_lines = []

    for line in _LINE_SPLIT_RE.split(text):
        if line == "":
            flush()
            continue
        if line.startswith(":"):
            continue

        if ":" in line:
            field, value = line.split(":", 1)
            if value.startswith(" "):
                value = value[1:]
        else:
            field = line
            value = ""

        if field == "event":
            event_type = value
        elif field == "data":
            data_lines.append(value)
        elif field == "id":
            if "\x00" not in value:
                event_id = value
        elif field == "retry":
            if value.isascii() and value.isdigit():
                retry = int(value)

    flush()
    return events


class SSEContentview(Contentview):
    name = "Server-Sent Events"
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        events = parse_sse(data)
        if not events:
            return "(no events)"
        return "\n---\n".join(yaml_dumps(event).rstrip("\n") for event in events)

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if data and metadata.content_type == "text/event-stream":
            return 1.0
        return 0


sse = SSEContentview()
