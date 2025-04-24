import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_xml_html import tokenize
from mitmproxy.contentviews._view_xml_html import xml_html

datadir = "mitmproxy/contentviews/test_xml_html_data/"


def test_simple(tdata):
    assert xml_html.prettify(b"foo", Metadata()) == "foo\n"
    assert xml_html.prettify(b"<html></html>", Metadata()) == "<html></html>\n"
    assert xml_html.prettify(b"<>", Metadata()) == "<>\n"
    assert xml_html.prettify(b"<p", Metadata()) == "<p\n"

    with open(tdata.path(datadir + "simple.html")) as f:
        input = f.read()
    tokens = tokenize(input)
    assert str(next(tokens)) == "Tag(<!DOCTYPE html>)"


@pytest.mark.parametrize(
    "filename", ["simple.html", "cdata.xml", "comment.xml", "inline.html", "test.html"]
)
def test_format_xml(filename, tdata):
    path = tdata.path(datadir + filename)
    with open(path, "rb") as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()

    assert xml_html.prettify(input, Metadata()) == expected


def test_render_priority():
    assert xml_html.render_priority(b"data", Metadata(content_type="text/xml"))
    assert xml_html.render_priority(b"data", Metadata(content_type="text/xml"))
    assert xml_html.render_priority(b"data", Metadata(content_type="text/html"))
    assert not xml_html.render_priority(b"data", Metadata(content_type="text/plain"))
    assert not xml_html.render_priority(b"", Metadata(content_type="text/xml"))
    assert xml_html.render_priority(b"<html/>", Metadata())
