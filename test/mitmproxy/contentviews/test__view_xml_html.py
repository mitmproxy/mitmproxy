import pytest

from mitmproxy import http
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


def test_use_text():
    meta1 = Metadata()
    meta2 = Metadata(
        http_message=http.Response.make(
            content=b"\xf8",
        )
    )
    assert xml_html.prettify(b"\xf8", meta1) != "ø\n"
    assert xml_html.prettify(b"\xf8", meta2) == "ø\n"


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


@pytest.mark.parametrize(
    "markup",
    [
        b'<p title="1 > 0">text</p>',
        b"<p title='1 > 0'>text</p>",
        b'<p title="a > b > c" other=">">text</p>',
        b'<p title="it\'s > zero">text</p>',
        b"<p title='say \"yes > no\"'>text</p>",
    ],
)
def test_quoted_tag_delimiters(markup):
    assert xml_html.prettify(markup, Metadata()) == markup.decode() + "\n"


def test_quoted_tag_delimiter_in_nested_element():
    markup = b'<root><item value="a > b"><child/></item></root>'
    assert xml_html.prettify(markup, Metadata()) == (
        '<root>\n  <item value="a > b">\n    <child/>\n  </item>\n</root>\n'
    )


@pytest.mark.parametrize(
    "markup",
    [
        b'<p title="a > b"/>',
        b'<p title="a > b">',
        b'<p title="unterminated > value',
        b'<p title="unterminated > value>',
        b'<!-- " > quoted -->',
        b'<![CDATA[" > quoted]]>',
    ],
)
def test_quoted_tag_delimiter_special_cases(markup):
    assert xml_html.prettify(markup, Metadata()) == markup.decode() + "\n"
