import pytest

from mitmproxy.proxy.mode_specs import ProxyMode, Socks5Mode


def test_parse():
    m = ProxyMode.parse("reverse:https://example.com/@127.0.0.1:443")
    m = ProxyMode.from_state(m.get_state())

    assert m.type == "reverse"
    assert m.full_spec == "reverse:https://example.com/@127.0.0.1:443"
    assert m.data == "https://example.com/"
    assert m.custom_listen_host == "127.0.0.1"
    assert m.custom_listen_port == 443

    with pytest.raises(ValueError, match="unknown mode"):
        ProxyMode.parse("flibbel")

    with pytest.raises(ValueError, match="invalid port"):
        ProxyMode.parse("regular@invalid-port")

    with pytest.raises(ValueError, match="invalid port"):
        ProxyMode.parse("regular@99999")

    m.set_state(m.get_state())
    with pytest.raises(RuntimeError, match="Proxy modes are frozen"):
        m.set_state("regular")


def test_parse_subclass():
    assert Socks5Mode.parse("socks5")
    with pytest.raises(ValueError, match="'regular' is not a spec for a socks5 mode"):
        Socks5Mode.parse("regular")


def test_listen_addr():
    assert ProxyMode.parse("regular").listen_port() == 8080
    assert ProxyMode.parse("regular@1234").listen_port() == 1234
    assert ProxyMode.parse("regular").listen_port(default=4424) == 4424
    assert ProxyMode.parse("regular@1234").listen_port(default=4424) == 1234

    assert ProxyMode.parse("regular").listen_host() == ""
    assert ProxyMode.parse("regular@127.0.0.2:8080").listen_host() == "127.0.0.2"
    assert ProxyMode.parse("regular").listen_host(default="127.0.0.3") == "127.0.0.3"
    assert ProxyMode.parse("regular@127.0.0.2:8080").listen_host(default="127.0.0.3") == "127.0.0.2"


def test_parse_specific_modes():
    assert ProxyMode.parse("regular")
    assert ProxyMode.parse("transparent")
    assert ProxyMode.parse("upstream:https://proxy")
    assert ProxyMode.parse("reverse:https://host@443")
    assert ProxyMode.parse("socks5")
    assert ProxyMode.parse("dns").resolve_local
    assert ProxyMode.parse("dns:reverse:8.8.8.8")

    with pytest.raises(ValueError, match="invalid port"):
        ProxyMode.parse("regular@invalid-port")

    with pytest.raises(ValueError, match="takes no arguments"):
        ProxyMode.parse("regular:configuration")

    with pytest.raises(ValueError, match="invalid upstream proxy scheme"):
        ProxyMode.parse("upstream:dns://example.com")

    with pytest.raises(ValueError, match="invalid reverse proxy scheme"):
        ProxyMode.parse("reverse:dns://example.com")

    with pytest.raises(ValueError, match="invalid dns mode"):
        ProxyMode.parse("dns:invalid")

    with pytest.raises(ValueError, match="invalid dns scheme"):
        ProxyMode.parse("dns:reverse:https://example.com")
