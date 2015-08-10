from cStringIO import StringIO
import socket
from nose.plugins.skip import SkipTest
from netlib import socks, tcp, tutils


def test_client_greeting():
    raw = tutils.treader("\x05\x02\x00\xBE\xEF")
    out = StringIO()
    msg = socks.ClientGreeting.from_file(raw)
    msg.assert_socks5()
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-1]
    assert msg.ver == 5
    assert len(msg.methods) == 2
    assert 0xBE in msg.methods
    assert 0xEF not in msg.methods


def test_client_greeting_assert_socks5():
    raw = tutils.treader("\x00\x00")
    msg = socks.ClientGreeting.from_file(raw)
    tutils.raises(socks.SocksError, msg.assert_socks5)

    raw = tutils.treader("HTTP/1.1 200 OK" + " " * 100)
    msg = socks.ClientGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" not in str(e)
    else:
        assert False

    raw = tutils.treader("GET / HTTP/1.1" + " " * 100)
    msg = socks.ClientGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" in str(e)
    else:
        assert False

    raw = tutils.treader("XX")
    tutils.raises(
        socks.SocksError,
        socks.ClientGreeting.from_file,
        raw,
        fail_early=True)


def test_server_greeting():
    raw = tutils.treader("\x05\x02")
    out = StringIO()
    msg = socks.ServerGreeting.from_file(raw)
    msg.assert_socks5()
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()
    assert msg.ver == 5
    assert msg.method == 0x02


def test_server_greeting_assert_socks5():
    raw = tutils.treader("HTTP/1.1 200 OK" + " " * 100)
    msg = socks.ServerGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" in str(e)
    else:
        assert False

    raw = tutils.treader("GET / HTTP/1.1" + " " * 100)
    msg = socks.ServerGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" not in str(e)
    else:
        assert False


def test_message():
    raw = tutils.treader("\x05\x01\x00\x03\x0bexample.com\xDE\xAD\xBE\xEF")
    out = StringIO()
    msg = socks.Message.from_file(raw)
    msg.assert_socks5()
    assert raw.read(2) == "\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.ver == 5
    assert msg.msg == 0x01
    assert msg.atyp == 0x03
    assert msg.addr == ("example.com", 0xDEAD)


def test_message_assert_socks5():
    raw = tutils.treader("\xEE\x01\x00\x03\x0bexample.com\xDE\xAD\xBE\xEF")
    msg = socks.Message.from_file(raw)
    tutils.raises(socks.SocksError, msg.assert_socks5)


def test_message_ipv4():
    # Test ATYP=0x01 (IPV4)
    raw = tutils.treader("\x05\x01\x00\x01\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    out = StringIO()
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == "\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.addr == ("127.0.0.1", 0xDEAD)


def test_message_ipv6():
    if not hasattr(socket, "inet_ntop"):
        raise SkipTest("Skipped because inet_ntop is not available")
    # Test ATYP=0x04 (IPV6)
    ipv6_addr = "2001:db8:85a3:8d3:1319:8a2e:370:7344"

    raw = tutils.treader(
        "\x05\x01\x00\x04" +
        socket.inet_pton(
            socket.AF_INET6,
            ipv6_addr) +
        "\xDE\xAD\xBE\xEF")
    out = StringIO()
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == "\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.addr.host == ipv6_addr


def test_message_invalid_rsv():
    raw = tutils.treader("\x05\x01\xFF\x01\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    tutils.raises(socks.SocksError, socks.Message.from_file, raw)


def test_message_unknown_atyp():
    raw = tutils.treader("\x05\x02\x00\x02\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    tutils.raises(socks.SocksError, socks.Message.from_file, raw)

    m = socks.Message(5, 1, 0x02, tcp.Address(("example.com", 5050)))
    tutils.raises(socks.SocksError, m.to_file, StringIO())
