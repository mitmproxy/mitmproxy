import json
import sys
from unittest import mock

import pytest
import urwid
import urwid.text_layout

from mitmproxy import http
from mitmproxy.test import tflow
from mitmproxy.tools.console.flowview import _CHARS_PER_LINE
from mitmproxy.tools.console.flowview import _CONTENT_TEXT_LAYOUT
from mitmproxy.tools.console.flowview import _LinearTextLayout
from mitmproxy.tools.console.flowview import FlowDetails
from mitmproxy.tools.console.searchable import Highlight


async def test_flowview(console):
    for f in tflow.tflows():
        console.commands.call("view.clear")
        await console.load_flow(f)
        console.type("<enter><tab><tab>")


def _edit(data: str) -> str:
    assert data == "hello: true\n"
    return "hello: false"


async def test_edit(console, monkeypatch, caplog):
    MSGPACK_WITH_TRUE = b"\x81\xa5hello\xc3"
    MSGPACK_WITH_FALSE = b"\x81\xa5hello\xc2"
    f = tflow.tflow(
        req=http.Request.make(
            "POST",
            "http://example.com",
            MSGPACK_WITH_TRUE,
            headers={"Content-Type": "application/msgpack"},
        )
    )
    await console.load_flow(f)
    monkeypatch.setattr(console, "spawn_editor", _edit)

    console.type(':console.edit.focus "request-body (MsgPack)"<enter><enter>')
    assert "hello: false" in console.screen_contents()
    assert f.request.content == MSGPACK_WITH_FALSE


async def test_content_missing_returns_error(console):
    # message.raw_content is None -> expect "[content missing]" error text
    f_missing = tflow.tflow(
        req=http.Request.make("GET", "http://example.com", b"initial"),
    )
    f_missing.request.raw_content = None

    await console.load_flow(f_missing)

    fd = FlowDetails(console)

    title, txt_objs = fd.content_view("default", f_missing.request)
    assert title == ""

    first_text = txt_objs[0].get_text()[0]
    assert "[content missing]" == first_text


async def test_empty_content_request_and_response(console):
    fd = FlowDetails(console)

    # 1) Request with empty body and no query -> "No request content"
    f_req_empty = tflow.tflow(
        req=http.Request.make("GET", "http://example.com", b""),
    )
    f_req_empty.request.raw_content = b""
    await console.load_flow(f_req_empty)
    title_req, txt_objs_req = fd.content_view("default", f_req_empty.request)
    assert title_req == ""
    req_text = txt_objs_req[0].get_text()[0]
    assert "No request content" == req_text

    # 2) Response with empty body -> "No content"
    f_resp_empty = tflow.tflow(
        req=http.Request.make("GET", "http://example.com", b""),
        resp=http.Response.make(200, b"", {}),
    )
    f_resp_empty.response.raw_content = b""
    await console.load_flow(f_resp_empty)
    title_resp, txt_objs_resp = fd.content_view("default", f_resp_empty.response)
    assert title_resp == ""
    resp_text = txt_objs_resp[0].get_text()[0]
    assert "No content" == resp_text


async def test_content_view_fullcontents_true_uses_unlimited_limit(console):
    f = tflow.tflow(req=http.Request.make("POST", "http://example.com", b"non-empty"))
    await console.load_flow(f)

    fd = FlowDetails(console)

    console.commands.execute("view.settings.setval @focus fullcontents true")
    fd._get_content_view = mock.MagicMock()
    fd.content_view("default", f.request)
    fd._get_content_view.assert_called_with("default", sys.maxsize, mock.ANY)


async def test_long_single_line_cutoff_and_fullcontents(console):
    # A large single-line JSON body has fewer newlines than content_view_lines_cutoff,
    # so it must still be truncated by wrapped line budget and render quickly.
    payload = json.dumps({"image": "A" * 100_000}).encode()
    f = tflow.tflow(
        req=http.Request.make(
            "POST",
            "http://example.com/upload",
            payload,
            headers={"Content-Type": "application/json"},
        )
    )
    await console.load_flow(f)
    console.type("<enter>")

    fd = console.window.current_window("flowview").body
    _, txt_objs = fd.content_view("auto", f.request)
    assert len(txt_objs) == 2
    assert len(txt_objs[0].get_text()[0]) == (
        console.options.content_view_lines_cutoff * _CHARS_PER_LINE
    )
    assert "Stopped displaying data" in txt_objs[1].get_text()[0]
    assert '"image"' in console.screen_contents()

    console.commands.execute("view.settings.setval @focus fullcontents true")
    _, full_objs = fd.content_view("auto", f.request)
    assert len(full_objs) == 1
    assert len(full_objs[0].get_text()[0]) > 100_000
    assert '"image"' in console.screen_contents()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        "\n\n",
        "hello world",
        "a" * 50,
        "hello\n\nworld\n",
        "中文测试 hello 世界\nnext",
        "e\u0301" * 10,
        "\u200b" * 5,
        b"hello world\n" + b"x" * 30,
    ],
)
@pytest.mark.parametrize("width", [2, 10, 80])
@pytest.mark.parametrize("wrap", ["any", "space"])
def test_linear_text_layout_matches_standard(text, width, wrap):
    std = urwid.StandardTextLayout()
    lin = _LinearTextLayout()
    assert lin.calculate_text_segments(text, width, wrap) == (
        std.calculate_text_segments(text, width, wrap)
    )


def test_linear_text_layout_narrow_wide_char():
    with pytest.raises(urwid.text_layout.CanNotDisplayText):
        _LinearTextLayout().calculate_text_segments("中", 1, "any")


def test_searchable_highlight_preserves_layout():
    orig = urwid.Text("hello", wrap="any", layout=_CONTENT_TEXT_LAYOUT)
    highlighted = Highlight(orig)
    assert highlighted.original_widget.wrap == "any"
    assert highlighted.original_widget.layout is _CONTENT_TEXT_LAYOUT
