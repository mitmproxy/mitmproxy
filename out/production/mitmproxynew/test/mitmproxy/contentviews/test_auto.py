from mitmproxy.contentviews import auto
from mitmproxy.test import tflow
from . import full_eval


def test_view_auto():
    v = full_eval(auto.ViewAuto())
    f = v(
        b"foo",
    )
    assert f[0] == "Raw"

    f = v(
        b"<html></html>",
        content_type="text/html",
    )
    assert f[0] == "HTML"

    f = v(
        b"foo",
        content_type="text/flibble",
    )
    assert f[0] == "Raw"

    f = v(
        b"<xml></xml>",
        content_type="text/flibble",
    )
    assert f[0].startswith("XML")

    f = v(
        b"<svg></svg>",
        content_type="image/svg+xml",
    )
    assert f[0].startswith("XML")

    f = v(
        b"{}",
        content_type="application/acme+json",
    )
    assert f[0].startswith("JSON")

    f = v(
        b"verybinary",
        content_type="image/new-magic-image-format",
    )
    assert f[0] == "Unknown Image"

    f = v(b"\xFF" * 30)
    assert f[0] == "Hex"

    f = v(
        b"",
    )
    assert f[0] == "No content"

    flow = tflow.tflow()
    flow.request.query = [("foo", "bar")]
    f = v(
        b"",
        flow=flow,
        http_message=flow.request,
    )
    assert f[0] == "Query"
