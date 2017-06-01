import pytest

from mitmproxy.contentviews import xml_html
from mitmproxy.test import tutils
from . import full_eval

data = tutils.test_data.push("mitmproxy/contentviews/test_xml_html_data/")


def test_simple():
    v = full_eval(xml_html.ViewXmlHtml())
    assert v(b"foo") == ('XML', [[('text', 'foo')]])
    assert v(b"<html></html>") == ('HTML', [[('text', '<html></html>')]])
    assert v(b"<>") == ('XML', [[('text', '<>')]])
    assert v(b"<p") == ('XML', [[('text', '<p')]])

    with open(data.path("simple.html")) as f:
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
def test_format_xml(filename):
    path = data.path(filename)
    with open(path) as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    tokens = xml_html.tokenize(input)
    assert xml_html.format_xml(tokens) == expected
