from mitmproxy import http
from mitmproxy.test import tflow
from mitmproxy.tools.console.flowview import FlowDetails


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
    assert "[content missing]" in first_text


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
    assert "No request content" in req_text

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
    assert "No content" in resp_text
