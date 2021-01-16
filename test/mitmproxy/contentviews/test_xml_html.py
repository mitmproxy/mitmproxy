import pytest

from mitmproxy.contentviews import xml_html
from . import full_eval

datadir = "mitmproxy/contentviews/test_xml_html_data/"


def test_simple(tdata):
    v = full_eval(xml_html.ViewXmlHtml())
    assert v(b"foo") == ('XML', [[('text', 'foo')]])
    assert v(b"<html></html>") == ('HTML', [[('text', '<html></html>')]])
    assert v(b"<>") == ('XML', [[('text', '<>')]])
    assert v(b"<p") == ('XML', [[('text', '<p')]])

    with open(tdata.path(datadir + "simple.html")) as f:
        input = f.read()
    tokens = xml_html.tokenize(input)
    assert str(next(tokens)) == "Tag(<!DOCTYPE html>)"


@pytest.mark.parametrize("filename", [
    "simple.html",
    "cdata.xml",
    "comment.xml",
    "inline.html",
    "test.html"
])
def test_format_xml(filename, tdata):
    path = tdata.path(datadir + filename)
    with open(path) as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    tokens = xml_html.tokenize(input)
    assert xml_html.format_xml(tokens) == expected


def test_render_priority():
    v = xml_html.ViewXmlHtml()
    assert v.render_priority(b"", content_type="text/xml")
    assert v.render_priority(b"", content_type="text/xml")
    assert v.render_priority(b"", content_type="text/html")
    assert not v.render_priority(b"", content_type="text/plain")
    assert v.render_priority(b"<html/>")
