from mitmproxy.contentviews import auto
from mitmproxy.net import http
from mitmproxy.types import multidict
from . import full_eval


def test_view_auto():
    v = full_eval(auto.ViewAuto())
    f = v(
        b"foo",
        headers=http.Headers()
    )
    assert f[0] == "Raw"

    f = v(
        b"<html></html>",
        headers=http.Headers(content_type="text/html")
    )
    assert f[0] == "HTML"

    f = v(
        b"foo",
        headers=http.Headers(content_type="text/flibble")
    )
    assert f[0] == "Raw"

    f = v(
        b"<xml></xml>",
        headers=http.Headers(content_type="text/flibble")
    )
    assert f[0].startswith("XML")

    f = v(
        b"<svg></svg>",
        headers=http.Headers(content_type="image/svg+xml")
    )
    assert f[0].startswith("XML")

    f = v(
        b"verybinary",
        headers=http.Headers(content_type="image/new-magic-image-format")
    )
    assert f[0] == "Unknown Image"

    f = v(b"\xFF" * 30)
    assert f[0] == "Hex"

    f = v(
        b"",
        headers=http.Headers()
    )
    assert f[0] == "No content"

    f = v(
        b"",
        headers=http.Headers(),
        query=multidict.MultiDict([("foo", "bar")]),
    )
    assert f[0] == "Query"
