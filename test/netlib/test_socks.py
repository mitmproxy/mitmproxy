import ipaddress
from io import BytesIO
import socket
from netlib import socks, tcp, tutils
from . import tservers


def test_client_greeting():
    raw = tutils.treader(b"\x05\x02\x00\xBE\xEF")
    out = BytesIO()
    msg = socks.ClientGreeting.from_file(raw)
    msg.assert_socks5()
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-1]
    assert msg.ver == 5
    assert len(msg.methods) == 2
    assert 0xBE in msg.methods
    assert 0xEF not in msg.methods


def test_client_greeting_assert_socks5():
    raw = tutils.treader(b"\x00\x00")
    msg = socks.ClientGreeting.from_file(raw)
    tutils.raises(socks.SocksError, msg.assert_socks5)

    raw = tutils.treader(b"HTTP/1.1 200 OK" + b" " * 100)
    msg = socks.ClientGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" not in str(e)
    else:
        assert False

    raw = tutils.treader(b"GET / HTTP/1.1" + b" " * 100)
    msg = socks.ClientGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" in str(e)
    else:
        assert False

    raw = tutils.treader(b"XX")
    tutils.raises(
        socks.SocksError,
        socks.ClientGreeting.from_file,
        raw,
        fail_early=True)


def test_server_greeting():
    raw = tutils.treader(b"\x05\x02")
    out = BytesIO()
    msg = socks.ServerGreeting.from_file(raw)
    msg.assert_socks5()
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()
    assert msg.ver == 5
    assert msg.method == 0x02


def test_server_greeting_assert_socks5():
    raw = tutils.treader(b"HTTP/1.1 200 OK" + b" " * 100)
    msg = socks.ServerGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" in str(e)
    else:
        assert False

    raw = tutils.treader(b"GET / HTTP/1.1" + b" " * 100)
    msg = socks.ServerGreeting.from_file(raw)
    try:
        msg.assert_socks5()
    except socks.SocksError as e:
        assert "Invalid SOCKS version" in str(e)
        assert "HTTP" not in str(e)
    else:
        assert False


def test_username_password_auth():
    raw = tutils.treader(b"\x01\x03usr\x03psd\xBE\xEF")
    out = BytesIO()
    auth = socks.UsernamePasswordAuth.from_file(raw)
    auth.assert_authver1()
    assert raw.read(2) == b"\xBE\xEF"
    auth.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert auth.ver == socks.USERNAME_PASSWORD_VERSION.DEFAULT
    assert auth.username == "usr"
    assert auth.password == "psd"


def test_username_password_auth_assert_ver1():
    raw = tutils.treader(b"\x02\x03usr\x03psd\xBE\xEF")
    auth = socks.UsernamePasswordAuth.from_file(raw)
    tutils.raises(socks.SocksError, auth.assert_authver1)


def test_username_password_auth_response():
    raw = tutils.treader(b"\x01\x00\xBE\xEF")
    out = BytesIO()
    auth = socks.UsernamePasswordAuthResponse.from_file(raw)
    auth.assert_authver1()
    assert raw.read(2) == b"\xBE\xEF"
    auth.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert auth.ver == socks.USERNAME_PASSWORD_VERSION.DEFAULT
    assert auth.status == 0


def test_username_password_auth_response_auth_assert_ver1():
    raw = tutils.treader(b"\x02\x00\xBE\xEF")
    auth = socks.UsernamePasswordAuthResponse.from_file(raw)
    tutils.raises(socks.SocksError, auth.assert_authver1)


def test_message():
    raw = tutils.treader(b"\x05\x01\x00\x03\x0bexample.com\xDE\xAD\xBE\xEF")
    out = BytesIO()
    msg = socks.Message.from_file(raw)
    msg.assert_socks5()
    assert raw.read(2) == b"\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.ver == 5
    assert msg.msg == 0x01
    assert msg.atyp == 0x03
    assert msg.addr == ("example.com", 0xDEAD)


def test_message_assert_socks5():
    raw = tutils.treader(b"\xEE\x01\x00\x03\x0bexample.com\xDE\xAD\xBE\xEF")
    msg = socks.Message.from_file(raw)
    tutils.raises(socks.SocksError, msg.assert_socks5)


def test_message_ipv4():
    # Test ATYP=0x01 (IPV4)
    raw = tutils.treader(b"\x05\x01\x00\x01\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    out = BytesIO()
    msg = socks.Message.from_file(raw)
    left = raw.read(2)
    assert left == b"\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.addr == ("127.0.0.1", 0xDEAD)


def test_message_ipv6():
    # Test ATYP=0x04 (IPV6)
    ipv6_addr = u"2001:db8:85a3:8d3:1319:8a2e:370:7344"

    raw = tutils.treader(
        b"\x05\x01\x00\x04" +
        ipaddress.IPv6Address(ipv6_addr).packed +
        b"\xDE\xAD\xBE\xEF")
    out = BytesIO()
    msg = socks.Message.from_file(raw)
    assert raw.read(2) == b"\xBE\xEF"
    msg.to_file(out)

    assert out.getvalue() == raw.getvalue()[:-2]
    assert msg.addr.host == ipv6_addr


def test_message_invalid_rsv():
    raw = tutils.treader(b"\x05\x01\xFF\x01\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    tutils.raises(socks.SocksError, socks.Message.from_file, raw)


def test_message_unknown_atyp():
    raw = tutils.treader(b"\x05\x02\x00\x02\x7f\x00\x00\x01\xDE\xAD\xBE\xEF")
    tutils.raises(socks.SocksError, socks.Message.from_file, raw)

    m = socks.Message(5, 1, 0x02, tcp.Address(("example.com", 5050)))
    tutils.raises(socks.SocksError, m.to_file, BytesIO())


class SocksHandler(tcp.BaseHandler):
    socksConfig = (None, None, True)

    @classmethod
    def getSocksConfig(cls):
        return cls.socksConfig

    def handle(self):
        username, password, succ = self.getSocksConfig()
        cgreeting = socks.ClientGreeting.from_file(self.rfile)
        assert cgreeting.ver == socks.VERSION.SOCKS5
        assert len(cgreeting.methods) == 2 or len(cgreeting.methods) == 1
        if len(cgreeting.methods) == 1:
            assert cgreeting.methods[0] == socks.METHOD.NO_AUTHENTICATION_REQUIRED
        else:
            assert cgreeting.methods[0] == socks.METHOD.NO_AUTHENTICATION_REQUIRED
            assert cgreeting.methods[1] == socks.METHOD.USERNAME_PASSWORD

        need_auth = False
        if username is None or password is None:
            sgreeting = socks.ServerGreeting(socks.VERSION.SOCKS5, socks.METHOD.NO_AUTHENTICATION_REQUIRED)
        elif len(cgreeting.methods) == 1:
            sgreeting = socks.ServerGreeting(socks.VERSION.SOCKS5, socks.METHOD.NO_ACCEPTABLE_METHODS)
        else:
            sgreeting = socks.ServerGreeting(socks.VERSION.SOCKS5, socks.METHOD.USERNAME_PASSWORD)
            need_auth = True
        sgreeting.to_file(self.wfile)
        self.wfile.flush()
        if need_auth:
            cauth = socks.UsernamePasswordAuth.from_file(self.rfile)
            assert cauth.ver == socks.USERNAME_PASSWORD_VERSION.DEFAULT
            if cauth.username == username and cauth.password == password:
                sauth = socks.UsernamePasswordAuthResponse(socks.USERNAME_PASSWORD_VERSION.DEFAULT, 0)
                sauth.to_file(self.wfile)
                self.wfile.flush()
            else:
                sauth = socks.UsernamePasswordAuthResponse(socks.USERNAME_PASSWORD_VERSION.DEFAULT, 1)
                sauth.to_file(self.wfile)
                self.wfile.flush()
                return
        cmsg = socks.Message.from_file(self.rfile)
        cmsg.assert_socks5()
        if succ:
            rep = socks.REP.SUCCEEDED
        else:
            rep = socks.REP.CONNECTION_NOT_ALLOWED_BY_RULESET
        connect_reply = socks.Message(
            socks.VERSION.SOCKS5,
            rep,
            cmsg.atyp,
            cmsg.addr
        )
        connect_reply.to_file(self.wfile)
        cmsg.to_file(self.wfile)


class TestSocksServerWithoutAuth(tservers.ServerTestBase):
    handler = SocksHandler

    def test_conn(self):
        test_addrs = [
            ("example.com", 12345, socks.ATYP.DOMAINNAME),
            ("127.0.0.1", 12345, socks.ATYP.IPV4_ADDRESS)
        ]
        if hasattr(socket, 'inet_pton'):
            test_addrs.append(("5aef:2b::8", 12345, socks.ATYP.IPV6_ADDRESS))
        for addr in test_addrs:
            ss = socks.SocksSocket("127.0.0.1", port = self.port)
            ss.connect((addr[0], addr[1]))
            rfile = tcp.Reader(ss.makefile("rb", False))
            cmsg = socks.Message.from_file(rfile)

            assert addr[0] == cmsg.addr.host
            assert addr[1] == cmsg.addr.port
            assert addr[2] == cmsg.atyp

    def test_conn_fail(self):
        self.handler.socksConfig = (None, None, False)
        test_addrs = [
            ("example.com", 12345, socks.ATYP.DOMAINNAME),
            ("127.0.0.1", 12345, socks.ATYP.IPV4_ADDRESS)
        ]
        if hasattr(socket, 'inet_pton'):
            test_addrs.append(("5aef:2b::8", 12345, socks.ATYP.IPV6_ADDRESS))
        for addr in test_addrs:
            ss = socks.SocksSocket("127.0.0.1", port = self.port)
            tutils.raises(socks.SocksError, ss.connect, (addr[0], addr[1]))


class TestSocksServerWithAuth(tservers.ServerTestBase):
    handler = SocksHandler

    def test_conn(self):
        self.handler.socksConfig = ("usr", "pwd", True)
        test_addrs = [
            ("example.com", 12345, socks.ATYP.DOMAINNAME),
            ("127.0.0.1", 12345, socks.ATYP.IPV4_ADDRESS)
        ]
        if hasattr(socket, 'inet_pton'):
            test_addrs.append(("5aef:2b::8", 12345, socks.ATYP.IPV6_ADDRESS))
        for addr in test_addrs:
            ss = socks.SocksSocket("127.0.0.1", port = self.port, username = "usr", password = "pwd")
            ss.connect((addr[0], addr[1]))
            rfile = tcp.Reader(ss.makefile("rb", False))
            cmsg = socks.Message.from_file(rfile)

            assert addr[0] == cmsg.addr.host
            assert addr[1] == cmsg.addr.port
            assert addr[2] == cmsg.atyp

    def test_auth_fail(self):
        self.handler.socksConfig = ("usr", "pwd", True)
        test_addrs = [
            ("example.com", 12345, socks.ATYP.DOMAINNAME),
            ("127.0.0.1", 12345, socks.ATYP.IPV4_ADDRESS)
        ]
        if hasattr(socket, 'inet_pton'):
            test_addrs.append(("5aef:2b::8", 12345, socks.ATYP.IPV6_ADDRESS))
        for addr in test_addrs:
            ss = socks.SocksSocket("127.0.0.1", port = self.port)
            tutils.raises(socks.SocksError, ss.connect, (addr[0], addr[1]))
