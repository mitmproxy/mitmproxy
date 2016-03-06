from __future__ import (absolute_import, print_function, division)
import struct
import array
import ipaddress
import socket
from . import tcp, utils


class SocksError(Exception):
    def __init__(self, code, message):
        super(SocksError, self).__init__(message)
        self.code = code

VERSION = utils.BiDi(
    SOCKS4=0x04,
    SOCKS5=0x05
)

CMD = utils.BiDi(
    CONNECT=0x01,
    BIND=0x02,
    UDP_ASSOCIATE=0x03
)

ATYP = utils.BiDi(
    IPV4_ADDRESS=0x01,
    DOMAINNAME=0x03,
    IPV6_ADDRESS=0x04
)

REP = utils.BiDi(
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

METHOD = utils.BiDi(
    NO_AUTHENTICATION_REQUIRED=0x00,
    GSSAPI=0x01,
    USERNAME_PASSWORD=0x02,
    NO_ACCEPTABLE_METHODS=0xFF
)

USERNAME_PASSWORD_VERSION = utils.BiDi(
    DEFAULT=0x01
)


class ClientGreeting(object):
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


class ServerGreeting(object):
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


class UsernamePasswordAuth(object):
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


class UsernamePasswordAuthResponse(object):
    __slots__  = ("ver", "status")

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


class Message(object):
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
            if not utils.is_valid_host(host):
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


class SocksSocket(socket.socket):
    __slots__ = ("conn_atype", "socks_address", "socks_port", "socks_username", "socks_password")

    def __init__(self, address, port = None, username = None, password = None, proto = 0, fileno = None):
        socks_addr_info = socket.getaddrinfo(address, port)
        socket.socket.__init__(self, socks_addr_info[0][0], socket.SOCK_STREAM, 0, fileno)
        self._set_proxy(address, port, username, password)

    def _set_proxy(self, address, port = None, username = None, password = None):
        self.socks_address = address
        if port is None:
            self.socks_port = 1080
        else:
            self.socks_port = port
        self.socks_username = username
        self.socks_password = password

    def _socks_username_password_auth(self, rfile, wfile):
        if self.socks_username is None or self.socks_password is None:
            raise SocksError(0, "authentication failed")
        cauth = UsernamePasswordAuth(USERNAME_PASSWORD_VERSION.DEFAULT, self.socks_username, self.socks_password)
        cauth.to_file(wfile)
        wfile.flush()
        sauth = UsernamePasswordAuthResponse.from_file(rfile)
        if sauth.status != 0:
            raise SocksError(0, "authentication failed")

    def _get_address(slef, destpair):
        if (type(destpair) not in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) is not str) or (type(destpair[1]) is not int):
            raise SocksError(0, "invalid data")
        try:
            taddr = socket.inet_aton(destpair[0])
            destpair = (taddr, destpair[1])
            return tcp.Address(destpair, False), ATYP.IPV4_ADDRESS
        except:
            try:
                taddr = socket.inet_pton(socket.AF_INET6, destpair[0])
                destpair = (taddr, destpair[1])
                return tcp.Address(destpair, True), ATYP.IPV6_ADDRESS
            except:
                return tcp.Address(destpair, False), ATYP.DOMAINNAME

    def connect(self, destpair):
        try:
            socket.socket.connect(self, (self.socks_address, self.socks_port))
        except socket.error as err:
            raise SocksError(0, repr(err))
        rfile = tcp.Reader(self.makefile("rb", -1))
        wfile = tcp.Writer(self.makefile("wb", -1))
        method = (METHOD.NO_AUTHENTICATION_REQUIRED,)
        if self.socks_username is not None and self.socks_password is not None:
            method = (METHOD.NO_AUTHENTICATION_REQUIRED, METHOD.USERNAME_PASSWORD)
        cgreeting = ClientGreeting(VERSION.SOCKS5, method)
        cgreeting.to_file(wfile)
        wfile.flush()
        sgreeting = ServerGreeting.from_file(rfile)
        if sgreeting.method == METHOD.NO_ACCEPTABLE_METHODS:
            raise SocksError(sgreeting.method, "no acceptable methods")
        if sgreeting.method == METHOD.USERNAME_PASSWORD:
            self._socks_username_password_auth(rfile, wfile)
        dst_addr, atype = self._get_address(destpair)
        cmsg = Message(VERSION.SOCKS5, CMD.CONNECT, atype, dst_addr)
        cmsg.to_file(wfile)
        wfile.flush()
        smsg = Message.from_file(rfile)
        if smsg.msg != REP.SUCCEEDED:
            raise SocksError(smsg.msg, "connect fail")
