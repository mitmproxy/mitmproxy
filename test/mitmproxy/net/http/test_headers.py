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
        ("text/html; charset=latin1", b"\xc3\xbc", "latin1"),
        ("text/html; charset=utf8", b"\xc3\xbc", "utf8"),
        # json
        ("application/json", b'"\xc3\xbc"', "utf8"),
        # meta charset
        (
            "text/html",
            b'<meta http-equiv="content-type" '
            b'content="text/html;charset=gb2312">\xe6\x98\x8e\xe4\xbc\xaf',
            "gb18030",
        ),
        # css charset
        (
            "text/css",
            b'@charset "gb2312";' b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}',
            "gb18030",
        ),
    ],
)
def test_infer_content_encoding(content_type, content, expected):
    # Additional test coverage in `test_http::TestMessageText`
    assert infer_content_encoding(content_type, content) == expected
