import pytest

from mitmproxy import http
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_multipart import multipart


def meta(content_type: str) -> Metadata:
    return Metadata(
        content_type=content_type.split(";")[0],
        http_message=http.Request.make(
            "POST", "https://example.com/", headers={"content-type": content_type}
        ),
    )


def test_view_multipart():
    v = b"""
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
    assert (
        multipart.prettify(v, meta("multipart/form-data; boundary=AaB03x"))
        == "submit-name: Larry\n"
    )

    with pytest.raises(ValueError):
        assert not multipart.prettify(v, Metadata())

    assert not multipart.prettify(v, meta("multipart/form-data"))

    assert not multipart.prettify(v, meta("unparseable"))


def test_render_priority():
    assert multipart.render_priority(
        b"data", Metadata(content_type="multipart/form-data")
    )
    assert not multipart.render_priority(b"data", Metadata(content_type="text/plain"))
