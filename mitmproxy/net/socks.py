import struct
import array
import ipaddress

from mitmproxy.net import tcp
from mitmproxy.net import check
from mitmproxy.types import bidi


class SocksError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


VERSION = bidi.BiDi(
    SOCKS4=0x04,
    SOCKS5=0x05
)

CMD = bidi.BiDi(
    CONNECT=0x01,
    BIND=0x02,
    UDP_ASSOCIATE=0x03
)

ATYP = bidi.BiDi(
    IPV4_ADDRESS=0x01,
    DOMAINNAME=0x03,
    IPV6_ADDRESS=0x04
)

REP = bidi.BiDi(
    SUCCEEDED=0x00,
    GENERAL_SOCKS_SERVER_FAILURE=0x01,
    CONNECTION_NOT_ALLOWED_BY_RULESET=0x02,
    NETWORK_UNREACHABLE=0x03,
    HOST_UNREACHABLE=0x04,
    CONNECTION_REFUSED=0x05,
    TTL_EXPIRED=0x06,
    COMMAND_NOT_SUPPORTED=0x07,
    ADDRESS_TYPE_NOT_SUPPORTED=0x08,
)

METHOD = bidi.BiDi(
    NO_AUTHENTICATION_REQUIRED=0x00,
    GSSAPI=0x01,
    USERNAME_PASSWORD=0x02,
    NO_ACCEPTABLE_METHODS=0xFF
)

USERNAME_PASSWORD_VERSION = bidi.BiDi(
    DEFAULT=0x01
)


class ClientGreeting:
    __slots__ = ("ver", "methods")

    def __init__(self, ver, methods):
        self.ver = ver
        self.methods = array.array("B")
        self.methods.extend(methods)

    def assert_socks5(self):
        if self.ver != VERSION.SOCKS5:
            if self.ver == ord("G") and len(self.methods) == ord("E"):
                guess = "Probably not a SOCKS request but a regular HTTP request. "
            else:
                guess = ""

            raise SocksError(
                REP.GENERAL_SOCKS_SERVER_FAILURE,
                guess + "Invalid SOCKS version. Expected 0x05, got 0x%x" % self.ver
            )

    @classmethod
    def from_file(cls, f, fail_early=False):
        """
        :param fail_early: If true, a SocksError will be raised if the first byte does not indicate socks5.
        """
        ver, nmethods = struct.unpack("!BB", f.safe_read(2))
        client_greeting = cls(ver, [])
        if fail_early:
            client_greeting.assert_socks5()
        client_greeting.methods.fromstring(f.safe_read(nmethods))
        return client_greeting

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, len(self.methods)))
        f.write(self.methods.tostring())


class ServerGreeting:
    __slots__ = ("ver", "method")

    def __init__(self, ver, method):
        self.ver = ver
        self.method = method

    def assert_socks5(self):
        if self.ver != VERSION.SOCKS5:
            if self.ver == ord("H") and self.method == ord("T"):
                guess = "Probably not a SOCKS request but a regular HTTP response. "
            else:
                guess = ""

            raise SocksError(
                REP.GENERAL_SOCKS_SERVER_FAILURE,
                guess + "Invalid SOCKS version. Expected 0x05, got 0x%x" % self.ver
            )

    @classmethod
    def from_file(cls, f):
        ver, method = struct.unpack("!BB", f.safe_read(2))
        return cls(ver, method)

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, self.method))


class UsernamePasswordAuth:
    __slots__ = ("ver", "username", "password")

    def __init__(self, ver, username, password):
        self.ver = ver
        self.username = username
        self.password = password

    def assert_authver1(self):
        if self.ver != USERNAME_PASSWORD_VERSION.DEFAULT:
            raise SocksError(
                0,
                "Invalid auth version. Expected 0x01, got 0x%x" % self.ver
            )

    @classmethod
    def from_file(cls, f):
        ver, ulen = struct.unpack("!BB", f.safe_read(2))
        username = f.safe_read(ulen)
        plen, = struct.unpack("!B", f.safe_read(1))
        password = f.safe_read(plen)
        return cls(ver, username.decode(), password.decode())

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, len(self.username)))
        f.write(self.username.encode())
        f.write(struct.pack("!B", len(self.password)))
        f.write(self.password.encode())


class UsernamePasswordAuthResponse:
    __slots__ = ("ver", "status")

    def __init__(self, ver, status):
        self.ver = ver
        self.status = status

    def assert_authver1(self):
        if self.ver != USERNAME_PASSWORD_VERSION.DEFAULT:
            raise SocksError(
                0,
                "Invalid auth version. Expected 0x01, got 0x%x" % self.ver
            )

    @classmethod
    def from_file(cls, f):
        ver, status = struct.unpack("!BB", f.safe_read(2))
        return cls(ver, status)

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, self.status))


class Message:
    __slots__ = ("ver", "msg", "atyp", "addr")

    def __init__(self, ver, msg, atyp, addr):
        self.ver = ver
        self.msg = msg
        self.atyp = atyp
        self.addr = tcp.Address.wrap(addr)

    def assert_socks5(self):
        if self.ver != VERSION.SOCKS5:
            raise SocksError(
                REP.GENERAL_SOCKS_SERVER_FAILURE,
                "Invalid SOCKS version. Expected 0x05, got 0x%x" % self.ver
            )

    @classmethod
    def from_file(cls, f):
        ver, msg, rsv, atyp = struct.unpack("!BBBB", f.safe_read(4))
        if rsv != 0x00:
            raise SocksError(
                REP.GENERAL_SOCKS_SERVER_FAILURE,
                "Socks Request: Invalid reserved byte: %s" % rsv
            )
        if atyp == ATYP.IPV4_ADDRESS:
            # We use tnoa here as ntop is not commonly available on Windows.
            host = ipaddress.IPv4Address(f.safe_read(4)).compressed
            use_ipv6 = False
        elif atyp == ATYP.IPV6_ADDRESS:
            host = ipaddress.IPv6Address(f.safe_read(16)).compressed
            use_ipv6 = True
        elif atyp == ATYP.DOMAINNAME:
            length, = struct.unpack("!B", f.safe_read(1))
            host = f.safe_read(length)
            if not check.is_valid_host(host):
                raise SocksError(REP.GENERAL_SOCKS_SERVER_FAILURE, "Invalid hostname: %s" % host)
            host = host.decode("idna")
            use_ipv6 = False
        else:
            raise SocksError(REP.ADDRESS_TYPE_NOT_SUPPORTED,
                             "Socks Request: Unknown ATYP: %s" % atyp)

        port, = struct.unpack("!H", f.safe_read(2))
        addr = tcp.Address((host, port), use_ipv6=use_ipv6)
        return cls(ver, msg, atyp, addr)

    def to_file(self, f):
        f.write(struct.pack("!BBBB", self.ver, self.msg, 0x00, self.atyp))
        if self.atyp == ATYP.IPV4_ADDRESS:
            f.write(ipaddress.IPv4Address(self.addr.host).packed)
        elif self.atyp == ATYP.IPV6_ADDRESS:
            f.write(ipaddress.IPv6Address(self.addr.host).packed)
        elif self.atyp == ATYP.DOMAINNAME:
            f.write(struct.pack("!B", len(self.addr.host)))
            f.write(self.addr.host.encode("idna"))
        else:
            raise SocksError(
                REP.ADDRESS_TYPE_NOT_SUPPORTED,
                "Unknown ATYP: %s" % self.atyp
            )
        f.write(struct.pack("!H", self.addr.port))
