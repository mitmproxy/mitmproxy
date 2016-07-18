from . import tutils
import base64
from mitmproxy.proxy import config


def test_parse_server_spec():
    tutils.raises(
        "Invalid server specification", config.parse_server_spec, ""
    )
    assert config.parse_server_spec("http://foo.com:88") == (
        b"http", (b"foo.com", 88)
    )
    assert config.parse_server_spec("http://foo.com") == (
        b"http", (b"foo.com", 80)
    )
    assert config.parse_server_spec("https://foo.com") == (
        b"https", (b"foo.com", 443)
    )
    tutils.raises(
        "Invalid server specification",
        config.parse_server_spec,
        "foo.com"
    )
    tutils.raises(
        "Invalid server specification",
        config.parse_server_spec,
        "http://"
    )


def test_parse_upstream_auth():
    tutils.raises(
        "Invalid upstream auth specification",
        config.parse_upstream_auth,
        ""
    )
    tutils.raises(
        "Invalid upstream auth specification",
        config.parse_upstream_auth,
        ":"
    )
    tutils.raises(
        "Invalid upstream auth specification",
        config.parse_upstream_auth,
        ":test"
    )
    assert config.parse_upstream_auth("test:test") == b"Basic" + b" " + base64.b64encode(b"test:test")
    assert config.parse_upstream_auth("test:") == b"Basic" + b" " + base64.b64encode(b"test:")
