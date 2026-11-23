import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews import prettify_message
from mitmproxy.contentviews import registry
from mitmproxy.contentviews._view_sse import parse_sse
from mitmproxy.contentviews._view_sse import sse
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_parse_sse_llm_stream():
    raw = (
        b"event: message_start\n"
        b"id: evt_1\n"
        b'data: {"type": "message_start", "model": "claude"}\n'
        b"\n"
        b"event: content_block_delta\n"
        b'data: {"delta": {"text": "\xe4\xbd\xa0\xe5\xa5\xbd"}}\n'
        b"\n"
        b"data: [DONE]\n"
        b"\n"
    )
    events = parse_sse(raw)
    assert events == [
        {
            "event": "message_start",
            "id": "evt_1",
            "data": {"type": "message_start", "model": "claude"},
        },
        {
            "event": "content_block_delta",
            "data": {"delta": {"text": "你好"}},
        },
        {
            "data": "[DONE]",
        },
    ]


def test_parse_sse_spec_edge_cases():
    # UTF-8 BOM, mixed CRLF/CR/LF endings, comments, multi-line data,
    # leading single space stripping, field without colon, retry, invalid id/retry,
    # unknown field, JSON array data, and unterminated trailing event.
    raw = (
        b"\xef\xbb\xbf"
        b": keep-alive comment\r\n"
        b"event:update\r\n"
        b"id: 42\r\n"
        b"retry: 3000\r\n"
        b"data:  two leading spaces\r\n"
        b"data:second line\r\n"
        b"unknown: ignored\r\n"
        b"\r\n"
        b"id: bad\x00id\r"
        b"retry: not-a-number\r"
        b"data\r"
        b"\r"
        b"retry: 5000\n"
        b"\n"
        b"data: [1, 2, 3]"
    )
    events = parse_sse(raw)
    assert events == [
        {
            "event": "update",
            "id": "42",
            "retry": 3000,
            "data": " two leading spaces\nsecond line",
        },
        {
            "data": "",
        },
        {
            "retry": 5000,
        },
        {
            "data": [1, 2, 3],
        },
    ]


def test_view_sse_prettify():
    meta = Metadata(content_type="text/event-stream")
    raw = b'event: delta\ndata: {"token": "hello"}\n\ndata: [DONE]\n\n'
    result = sse.prettify(raw, meta)
    assert "event: delta" in result
    assert "token: hello" in result
    assert "\n---\n" in result
    assert "data: '[DONE]'" in result or "data: [DONE]" in result
    assert sse.syntax_highlight == "yaml"
    assert sse.name == "Server-Sent Events"


def test_view_sse_empty_and_comments_only():
    meta = Metadata(content_type="text/event-stream")
    assert sse.prettify(b"", meta) == "(no events)"
    assert sse.prettify(b": heartbeat\n\n: another comment\n", meta) == "(no events)"


def test_view_sse_invalid_utf8_and_fallback():
    meta = Metadata(content_type="text/event-stream")
    with pytest.raises(ValueError):
        sse.prettify(b"\xff\xfe\x00", meta)

    with taddons.context():
        f = tflow.tflow(resp=True)
        assert f.response
        f.response.headers["content-type"] = "text/event-stream; charset=utf-8"
        f.response.content = b"\xff\xfe\x00"
        res = prettify_message(f.response, f, "auto")
        assert res.view_name == "Raw"
        assert "[failed to parse as Server-Sent Events]" in res.description


def test_render_priority():
    assert (
        sse.render_priority(b"data: hi\n\n", Metadata(content_type="text/event-stream"))
        == 1.0
    )
    assert sse.render_priority(b"", Metadata(content_type="text/event-stream")) == 0
    assert (
        sse.render_priority(b"data: hi\n\n", Metadata(content_type="text/plain")) == 0
    )
    assert sse.render_priority(b"data: hi\n\n", Metadata()) == 0
    assert (
        registry.get_view(
            b"data: hi\n\n", Metadata(content_type="text/event-stream")
        ).name
        == "Server-Sent Events"
    )
