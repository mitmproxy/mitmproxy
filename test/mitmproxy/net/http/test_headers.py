import collections

import pytest

from mitmproxy.net.http.headers import assemble_content_type
from mitmproxy.net.http.headers import infer_content_encoding
from mitmproxy.net.http.headers import parse_content_type


def test_parse_content_type():
    p = parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") is None

    v = p("text/html; charset=UTF-8")
    assert v == ("text", "html", {"charset": "UTF-8"})


def test_assemble_content_type():
    p = assemble_content_type
    assert p("text", "html", {}) == "text/html"
    assert p("text", "html", {"charset": "utf8"}) == "text/html; charset=utf8"
    assert (
        p(
            "text",
            "html",
            collections.OrderedDict([("charset", "utf8"), ("foo", "bar")]),
        )
        == "text/html; charset=utf8; foo=bar"
    )


@pytest.mark.parametrize(
    "content_type,content,expected",
    [
        ("", b"", "latin-1"),
        ("", b"foo", "latin-1"),
        ("", b"\xfc", "latin-1"),
        ("", b"\xf0\xe2", "latin-1"),
        # bom
        ("", b"\xef\xbb\xbffoo", "utf-8-sig"),
        ("", b"\xff\xfef\x00o\x00o\x00", "utf-16le"),
        ("", b"\xfe\xff\x00f\x00o\x00o", "utf-16be"),
        ("", b"\xff\xfe\x00\x00f\x00\x00\x00o\x00\x00\x00o\x00\x00\x00", "utf-32le"),
        ("", b"\x00\x00\xfe\xff\x00\x00\x00f\x00\x00\x00o\x00\x00\x00o", "utf-32be"),
        # content-type charset
        ("text/html; charset=latin1", b"\xc3\xbc", "latin1"),
        ("text/html; charset=utf8", b"\xc3\xbc", "utf8"),
        # json
        ("application/json", b'"\xc3\xbc"', "utf8"),
        # html meta charset
        # miss meta
        (
            "text/html",
            b'<charset="gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "utf8",
        ),
        (
            "text/html",
            b'<meta charset="gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        (
            "text/html",
            b'<meta http-equiv="content-type" '
            b'content="text/html;charset=gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        (
            "text/html",
            b'<meta http-equiv="content-type" '
            b'content="text/html;charset =gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        (
            "text/html",
            b'<meta http-equiv="content-type" '
            b'content="text/html;charset= gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        (
            "text/html",
            b'<meta http-equiv="content-type" '
            b'content="text/html;charset=gb2312;">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        (
            "text/html",
            b"<html></html>",
            "utf8",
        ),
        (
            "text/html",
            b'<meta charset="utf-8" >',
            "utf-8",
        ),
        (
            "text/html",
            b'<meta charset= "utf-8" >',
            "utf-8",
        ),
        (
            "text/html",
            b'<meta charset ="utf-8" >',
            "utf-8",
        ),
        # Case: Mismatched quotes
        (
            "text/html",
            b"<meta charset=\"utf-8' >",
            "utf8",
        ),
        (
            "text/html",
            b'<meta charset=" utf-8" >',
            "utf-8",
        ),
        (
            "text/html",
            b'<meta charset="utf-8 " >',
            "utf-8",
        ),
        (
            "text/html",
            b"<meta charset=utf-8>",
            "utf-8",
        ),
        (
            "text/html",
            b"<meta charset=utf-8 id=meta>",
            "utf-8",
        ),
        (
            "text/html",
            b'<meta http-equiv="Content-Type" content="text/html; charset=utf-8 version=2">',
            "utf-8",
        ),
        (
            "text/html",
            b"<meta charset=utf-8\nfoo=bar>",
            "utf-8",
        ),
        (
            "text/html",
            b"<meta charset=utf-8\tid=head>",
            "utf-8",
        ),
        (
            "text/html",
            b"<meta charset=''",
            "utf8",
        ),
        (
            "text/html",
            b"<meta charset=",
            "utf8",
        ),
        # xml declaration encoding
        (
            "application/xml",
            b'<?xml version="1.0" encoding="gb2312"?>'
            b"<root>\xe6\x98\x8e\xe4\xbc\xaf</root>",
            "gb18030",
        ),
        (
            "application/xml",
            b'<?xml version="1.0"?>',
            "utf8",
        ),
        # css charset
        (
            "text/css",
            b'\xef\xbb\xbf@charset "UTF-8";.\xe5\xb9\xb3\xe5\x92\x8c,#div2 {color: green;}',
            "utf-8-sig",
        ),
        (
            "text/css",
            b'@charset "gb2312";#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}',
            "gb18030",
        ),
        (
            "text/css",
            b"h1 {}",
            "utf8",
        ),
        # js
        ("application/javascript", b"", "utf8"),
        ("application/ecmascript", b"", "utf8"),
        ("text/javascript", b"", "utf8"),
    ],
)
def test_infer_content_encoding(content_type, content, expected):
    # Additional test coverage in `test_http::TestMessageText`
    assert infer_content_encoding(content_type, content) == expected
