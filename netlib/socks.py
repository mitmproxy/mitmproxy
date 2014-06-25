import socket
import struct
from array import array
from . import tcp, utils


class SocksError(Exception):
    def __init__(self, code, message):
        super(SocksError, self).__init__(message)
        self.code = code


class VERSION:
    SOCKS4 = 0x04
    SOCKS5 = 0x05


class CMD:
    CONNECT = 0x01
    BIND = 0x02
    UDP_ASSOCIATE = 0x03


class ATYP:
    IPV4_ADDRESS = 0x01
    DOMAINNAME = 0x03
    IPV6_ADDRESS = 0x04


class REP:
    SUCCEEDED = 0x00
    GENERAL_SOCKS_SERVER_FAILURE = 0x01
    CONNECTION_NOT_ALLOWED_BY_RULESET = 0x02
    NETWORK_UNREACHABLE = 0x03
    HOST_UNREACHABLE = 0x04
    CONNECTION_REFUSED = 0x05
    TTL_EXPIRED = 0x06
    COMMAND_NOT_SUPPORTED = 0x07
    ADDRESS_TYPE_NOT_SUPPORTED = 0x08


class METHOD:
    NO_AUTHENTICATION_REQUIRED = 0x00
    GSSAPI = 0x01
    USERNAME_PASSWORD = 0x02
    NO_ACCEPTABLE_METHODS = 0xFF


class ClientGreeting(object):
    __slots__ = ("ver", "methods")

    def __init__(self, ver, methods):
        self.ver = ver
        self.methods = methods

    @classmethod
    def from_file(cls, f):
        ver, nmethods = struct.unpack("!BB", f.read(2))
        methods = array("B")
        methods.fromstring(f.read(nmethods))
        return cls(ver, methods)

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, len(self.methods)))
        f.write(self.methods.tostring())

class ServerGreeting(object):
    __slots__ = ("ver", "method")

    def __init__(self, ver, method):
        self.ver = ver
        self.method = method

    @classmethod
    def from_file(cls, f):
        ver, method = struct.unpack("!BB", f.read(2))
        return cls(ver, method)

    def to_file(self, f):
        f.write(struct.pack("!BB", self.ver, self.method))

class Message(object):
    __slots__ = ("ver", "msg", "atyp", "addr")

    def __init__(self, ver, msg, atyp, addr):
        self.ver = ver
        self.msg = msg
        self.atyp = atyp
        self.addr = addr

    @classmethod
    def from_file(cls, f):
        ver, msg, rsv, atyp = struct.unpack("!BBBB", f.read(4))
        if rsv != 0x00:
            raise SocksError(REP.GENERAL_SOCKS_SERVER_FAILURE,
                             "Socks Request: Invalid reserved byte: %s" % rsv)

        if atyp == ATYP.IPV4_ADDRESS:
            host = utils.inet_ntop(socket.AF_INET, f.read(4))  # We use tnoa here as ntop is not commonly available on Windows.
            use_ipv6 = False
        elif atyp == ATYP.IPV6_ADDRESS:
            host = utils.inet_ntop(socket.AF_INET6, f.read(16))
            use_ipv6 = True
        elif atyp == ATYP.DOMAINNAME:
            length, = struct.unpack("!B", f.read(1))
            host = f.read(length)
            use_ipv6 = False
        else:
            raise SocksError(REP.ADDRESS_TYPE_NOT_SUPPORTED,
                             "Socks Request: Unknown ATYP: %s" % atyp)

        port, = struct.unpack("!H", f.read(2))
        addr = tcp.Address((host, port), use_ipv6=use_ipv6)
        return cls(ver, msg, atyp, addr)

    def to_file(self, f):
        f.write(struct.pack("!BBBB", self.ver, self.msg, 0x00, self.atyp))
        if self.atyp == ATYP.IPV4_ADDRESS:
            f.write(utils.inet_pton(socket.AF_INET, self.addr.host))
        elif self.atyp == ATYP.IPV6_ADDRESS:
            f.write(utils.inet_pton(socket.AF_INET6, self.addr.host))
        elif self.atyp == ATYP.DOMAINNAME:
            f.write(struct.pack("!B", len(self.addr.host)))
            f.write(self.addr.host)
        else:
            raise SocksError(REP.ADDRESS_TYPE_NOT_SUPPORTED, "Unknown ATYP: %s" % self.atyp)
        f.write(struct.pack("!H", self.addr.port))