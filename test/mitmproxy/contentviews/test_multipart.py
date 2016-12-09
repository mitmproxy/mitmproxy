from mitmproxy.contentviews import multipart
from mitmproxy.net import http
from . import full_eval


def test_view_multipart():
    view = full_eval(multipart.ViewMultipart())
    v = b"""
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
    h = http.Headers(content_type="multipart/form-data; boundary=AaB03x")
    assert view(v, headers=h)

    h = http.Headers()
    assert not view(v, headers=h)

    h = http.Headers(content_type="multipart/form-data")
    assert not view(v, headers=h)

    h = http.Headers(content_type="unparseable")
    assert not view(v, headers=h)
