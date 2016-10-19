"""
We try to be very hygienic regarding the exceptions we throw:

- Every exception that might be externally visible to users shall be a subclass
  of ProxyException.p
- Every exception in the base net module shall be a subclass
  of NetlibException, and will not be propagated directly to users.

See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""


class ProxyException(Exception):

    """
    Base class for all exceptions thrown by mitmproxy.
    """

    def __init__(self, message=None):
        super().__init__(message)


class Kill(ProxyException):

    """
    Signal that both client and server connection(s) should be killed immediately.
    """
    pass


class ProtocolException(ProxyException):
    """
    ProtocolExceptions are caused by invalid user input, unavailable network resources,
    or other events that are outside of our influence.
    """
    pass


class TlsProtocolException(ProtocolException):
    pass


class ClientHandshakeException(TlsProtocolException):

    def __init__(self, message, server):
        super().__init__(message)
        self.server = server


class InvalidServerCertificate(TlsProtocolException):
    def __repr__(self):
        # In contrast to most others, this is a user-facing error which needs to look good.
        return str(self)


class Socks5ProtocolException(ProtocolException):
    pass


class HttpProtocolException(ProtocolException):
    pass


class Http2ProtocolException(ProtocolException):
    pass


class Http2ZombieException(ProtocolException):
    pass


class ServerException(ProxyException):
    pass


class ContentViewException(ProxyException):
    pass


class ReplayException(ProxyException):
    pass


class FlowReadException(ProxyException):
    pass


class ControlException(ProxyException):
    pass


class SetServerNotAllowedException(ProxyException):
    pass


class OptionsError(Exception):
    pass


class AddonError(Exception):
    pass


class AddonHalt(Exception):
    pass


"""
    Every net Exception raised shall be a subclass of NetlibException.
"""


class NetlibException(Exception):
    """
    Base class for all exceptions thrown by netlib.
    """
    def __init__(self, message=None):
        super().__init__(message)


class Disconnect:
    """Immediate EOF"""


class HttpException(NetlibException):
    pass


class HttpReadDisconnect(HttpException, Disconnect):
    pass


class HttpSyntaxException(HttpException):
    pass


class TcpException(NetlibException):
    pass


class TcpDisconnect(TcpException, Disconnect):
    pass


class TcpReadIncomplete(TcpException):
    pass


class TcpTimeout(TcpException):
    pass


class TlsException(NetlibException):
    pass


class InvalidCertificateException(TlsException):
    pass


class Timeout(TcpException):
    pass
