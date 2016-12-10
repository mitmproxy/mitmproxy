from mitmproxy.contentviews import html_outline
from test.mitmproxy.contentviews import full_eval


def test_view_html_outline():
    v = full_eval(html_outline.ViewHTMLOutline())
    s = b"<html><br><br></br><p>one</p></html>"
    assert v(s)
    assert v(b'\xfe')