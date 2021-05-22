import collections

from mitmproxy.net.http.headers import parse_content_type, assemble_content_type


def test_parse_content_type():
    p = parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") is None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})


def test_assemble_content_type():
    p = assemble_content_type
    assert p("text", "html", {}) == "text/html"
    assert p("text", "html", {"charset": "utf8"}) == "text/html; charset=utf8"
    assert p("text", "html",
             collections.OrderedDict([("charset", "utf8"), ("foo", "bar")])) == "text/html; charset=utf8; foo=bar"
