from mitmproxy import http
from mitmproxy.test import tflow


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
