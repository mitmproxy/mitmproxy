import socket
import struct
from array import array
from .tcp import Address


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
        ver, nmethods = struct.unpack_from("!BB", f)
        methods = array("B")
        methods.fromfile(f, nmethods)
        return cls(ver, methods)

    def to_file(self, f):
        struct.pack_into("!BB", f, 0, self.ver, len(self.methods))
        self.methods.tofile(f)


class ServerGreeting(object):
    __slots__ = ("ver", "method")

    def __init__(self, ver, method):
        self.ver = ver
        self.method = method

    @classmethod
    def from_file(cls, f):
        ver, method = struct.unpack_from("!BB", f)
        return cls(ver, method)

    def to_file(self, f):
        struct.pack_into("!BB", f, 0, self.ver, self.method)


class Request(object):
    __slots__ = ("ver", "cmd", "atyp", "dst")

    def __init__(self, ver, cmd, atyp, dst):
        self.ver = ver
        self.cmd = cmd
        self.atyp = atyp
        self.dst = dst

    @classmethod
    def from_file(cls, f):
        ver, cmd, rsv, atyp = struct.unpack_from("!BBBB", f)
        if rsv != 0x00:
            raise SocksError(REP.GENERAL_SOCKS_SERVER_FAILURE,
                             "Socks Request: Invalid reserved byte: %s" % rsv)

        if atyp == ATYP.IPV4_ADDRESS:
            host = socket.inet_ntoa(f.read(4))  # We use tnoa here as ntop is not commonly available on Windows.
            use_ipv6 = False
        elif atyp == ATYP.IPV6_ADDRESS:
            host = socket.inet_ntop(socket.AF_INET6, f.read(16))
            use_ipv6 = True
        elif atyp == ATYP.DOMAINNAME:
            length = struct.unpack_from("!B", f)
            host = f.read(length)
            use_ipv6 = False
        else:
            raise SocksError(REP.ADDRESS_TYPE_NOT_SUPPORTED,
                             "Socks Request: Unknown ATYP: %s" % atyp)

        port = struct.unpack_from("!H", f)
        dst = Address(host, port, use_ipv6=use_ipv6)
        return Request(ver, cmd, atyp, dst)

    def to_file(self, f):
        raise NotImplementedError()

class Reply(object):
    __slots__ = ("ver", "rep", "atyp", "bnd")

    def __init__(self, ver, rep, atyp, bnd):
        self.ver = ver
        self.rep = rep
        self.atyp = atyp
        self.bnd = bnd

    @classmethod
    def from_file(cls, f):
        raise NotImplementedError()

    def to_file(self, f):
        struct.pack_into("!BBBB", f, 0, self.ver, self.rep, 0x00, self.atyp)
        if self.atyp == ATYP.IPV4_ADDRESS:
            f.write(socket.inet_aton(self.bnd.host))
        elif self.atyp == ATYP.IPV6_ADDRESS:
            f.write(socket.inet_pton(socket.AF_INET6, self.bnd.host))
        elif self.atyp == ATYP.DOMAINNAME:
            struct.pack_into("!B", f, 0, len(self.bnd.host))
            f.write(self.bnd.host)
        else:
            raise SocksError(REP.ADDRESS_TYPE_NOT_SUPPORTED, "Unknown ATYP: %s" % self.atyp)
        struct.pack_into("!H", f, 0, self.bnd.port)