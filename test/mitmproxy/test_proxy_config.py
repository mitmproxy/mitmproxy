from mitmproxy.test import tutils
from mitmproxy.proxy import config


def test_parse_server_spec():
    tutils.raises(
        "Invalid server specification", config.parse_server_spec, ""
    )
    assert config.parse_server_spec("http://foo.com:88") == (
        "http", ("foo.com", 88)
    )
    assert config.parse_server_spec("http://foo.com") == (
        "http", ("foo.com", 80)
    )
    assert config.parse_server_spec("https://foo.com") == (
        "https", ("foo.com", 443)
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
