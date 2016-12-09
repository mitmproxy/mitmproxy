from mitmproxy.contentviews import html
from . import full_eval


def test_view_html():
    v = full_eval(html.ViewHTML())
    s = b"<html><br><br></br><p>one</p></html>"
    assert v(s)

    s = b"gobbledygook"
    assert not v(s)


def test_view_html_outline():
    v = full_eval(html.ViewHTMLOutline())
    s = b"<html><br><br></br><p>one</p></html>"
    assert v(s)
    assert v(b'\xfe')
