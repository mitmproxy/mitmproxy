import pytest

from mitmproxy.proxy.mode_specs import ProxyMode, Socks5Mode, WireGuardMode


def test_parse():
    m = ProxyMode.parse("reverse:https://example.com/@127.0.0.1:443")
    m = ProxyMode.from_state(m.get_state())

    assert m.type == "reverse"
    assert m.full_spec == "reverse:https://example.com/@127.0.0.1:443"
    assert m.data == "https://example.com/"
    assert m.custom_listen_host == "127.0.0.1"
    assert m.custom_listen_port == 443
    assert repr(m) == "ProxyMode.parse('reverse:https://example.com/@127.0.0.1:443')"

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

    assert ProxyMode.parse("reverse:https://1.2.3.4").listen_port() == 8080
    assert ProxyMode.parse("reverse:dns://8.8.8.8").listen_port() == 53


def test_parse_specific_modes():
    assert ProxyMode.parse("regular")
    assert ProxyMode.parse("transparent")
    assert ProxyMode.parse("upstream:https://proxy")
    assert ProxyMode.parse("reverse:https://host@443")
    assert ProxyMode.parse("socks5")
    assert ProxyMode.parse("dns")
    assert ProxyMode.parse("reverse:dns://8.8.8.8")
    assert ProxyMode.parse("reverse:dtls://127.0.0.1:8004")
    assert ProxyMode.parse("wireguard")
    assert ProxyMode.parse("wireguard@51821").listen_port() == 51821

    with pytest.raises(ValueError, match="invalid port"):
        ProxyMode.parse("regular@invalid-port")

    with pytest.raises(ValueError, match="takes no arguments"):
        ProxyMode.parse("regular:configuration")

    with pytest.raises(ValueError, match="invalid upstream proxy scheme"):
        ProxyMode.parse("upstream:dns://example.com")

    with pytest.raises(ValueError, match="takes no arguments"):
        ProxyMode.parse("dns:invalid")

    with pytest.raises(ValueError, match="Port specification missing."):
        ProxyMode.parse("reverse:dtls://127.0.0.1")


def test_parse_wireguard_mode():
    assert WireGuardMode.parse("wireguard:load,")
    assert WireGuardMode.parse("wireguard:generate,peers=2").wireguard_peer_num == 2
    assert WireGuardMode.parse("wireguard:load=~/.mitmproxy/wg.json").wireguard_cfg_path == "~/.mitmproxy/wg.json"

    mode = WireGuardMode.parse("wireguard:generate,peers=2@51821")
    assert mode.listen_port() == 51821
    assert mode.wireguard_cfg_gen is True
    assert mode.wireguard_peer_num == 2

    with pytest.raises(ValueError, match="cannot set both 'load' and 'generate'"):
        WireGuardMode.parse("wireguard:load,generate")
    with pytest.raises(ValueError, match="cannot set both 'load' and 'generate'"):
        WireGuardMode.parse("wireguard:generate,load")
    with pytest.raises(ValueError, match=f"unexpected 'peers=2' setting"):
        WireGuardMode.parse("wireguard:load,peers=2")
    with pytest.raises(ValueError, match="unexpected 'foobar' setting"):
        WireGuardMode.parse("wireguard:foobar")
    with pytest.raises(ValueError, match=f"invalid peer number 'foo'"):
        WireGuardMode.parse("wireguard:generate,peers=foo")
