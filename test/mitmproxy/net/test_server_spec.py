import pytest

from mitmproxy.net import server_spec


@pytest.mark.parametrize(
    "spec,default_scheme,out",
    [
        ("example.com", "https", ("https", ("example.com", 443))),
        ("http://example.com", "https", ("http", ("example.com", 80))),
        ("smtp.example.com:25", "tcp", ("tcp", ("smtp.example.com", 25))),
        ("http://127.0.0.1", "https", ("http", ("127.0.0.1", 80))),
        ("http://[::1]", "https", ("http", ("::1", 80))),
        ("http://[::1]/", "https", ("http", ("::1", 80))),
        ("https://[::1]/", "https", ("https", ("::1", 443))),
        ("http://[::1]:8080", "https", ("http", ("::1", 8080))),
    ],
)
def test_parse(spec, default_scheme, out):
    assert server_spec.parse(spec, default_scheme) == out


def test_parse_err():
    with pytest.raises(ValueError, match="Invalid server specification"):
        server_spec.parse(":", "https")

    with pytest.raises(ValueError, match="Invalid server scheme"):
        server_spec.parse("ftp://example.com", "https")

    with pytest.raises(ValueError, match="Invalid hostname"):
        server_spec.parse("$$$", "https")

    with pytest.raises(ValueError, match="Invalid port"):
        server_spec.parse("example.com:999999", "https")

    with pytest.raises(ValueError, match="Port specification missing"):
        server_spec.parse("example.com", "tcp")
