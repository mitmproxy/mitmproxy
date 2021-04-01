import pytest

from mitmproxy.net import server_spec


@pytest.mark.parametrize("spec,out", [
    ("example.com", ("https", ("example.com", 443))),
    ("http://example.com", ("http", ("example.com", 80))),
    ("smtp.example.com:25", ("http", ("smtp.example.com", 25))),
    ("http://127.0.0.1", ("http", ("127.0.0.1", 80))),
    ("http://[::1]", ("http", ("::1", 80))),
    ("http://[::1]/", ("http", ("::1", 80))),
    ("https://[::1]/", ("https", ("::1", 443))),
    ("http://[::1]:8080", ("http", ("::1", 8080))),
])
def test_parse(spec, out):
    assert server_spec.parse(spec) == out


def test_parse_err():
    with pytest.raises(ValueError, match="Invalid server specification"):
        server_spec.parse(":")

    with pytest.raises(ValueError, match="Invalid server scheme"):
        server_spec.parse("ftp://example.com")

    with pytest.raises(ValueError, match="Invalid hostname"):
        server_spec.parse("$$$")

    with pytest.raises(ValueError, match="Invalid port"):
        server_spec.parse("example.com:999999")


def test_parse_with_mode():
    assert server_spec.parse_with_mode("m:example.com") == ("m", ("https", ("example.com", 443)))
    with pytest.raises(ValueError):
        server_spec.parse_with_mode("moo")
