from cStringIO import StringIO
import socket
from nose.plugins.skip import SkipTest
from netlib import socks, utils
import tutils


def test_client_greeting():
    raw = StringIO("\x05\x02\x00\xBE\xEF")
    out = StringIO()
    msg = socks.ClientGreeting.from_file(raw)
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-1]
    assert msg.ver == 5
    assert len(msg.methods) == 2
    assert 0xBE in msg.methods
    assert 0xEF not in msg.methods


def test_server_greeting():
    raw = StringIO("\x05\x02")
    out = StringIO()
    msg = socks.ServerGreeting.from_file(raw)
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()
    assert msg.ver == 5
    assert msg.method == 0x02


def test_message():
    raw = StringIO("\x05\x01\x00\x03\x0bexample.com\xDE\xAD\xBE\xEF")
    out = StringIO()
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == "\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.ver == 5
    assert msg.msg == 0x01
    assert msg.atyp == 0x03
    assert msg.addr == ("example.com", 0xDEAD)

    # Test ATYP=0x01 (IPV4)
    raw = StringIO("\x05\x01\x00\x01\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == "\xBE\xEF"
    assert msg.addr == ("127.0.0.1", 0xDEAD)


def test_message_ipv6():
    if not hasattr(socket, "inet_ntop"):
        raise SkipTest("Skipped because inet_ntop is not available")
    # Test ATYP=0x04 (IPV6)
    ipv6_addr = "2001:0db8:85a3:08d3:1319:8a2e:0370:7344"
    raw = StringIO("\x05\x01\x00\x04" + socket.inet_pton(socket.AF_INET6, ipv6_addr) + "\xDE\xAD\xBE\xEF")
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == "\xBE\xEF"
    assert msg.addr.host == ipv6_addr