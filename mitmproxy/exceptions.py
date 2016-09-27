"""
We try to be very hygienic regarding the exceptions we throw:
Every Exception mitmproxy raises shall be a subclass of ProxyException.


See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""
from __future__ import absolute_import, print_function, division


class ProxyException(Exception):

    """
    Base class for all exceptions thrown by mitmproxy.
    """

    def __init__(self, message=None):
        super(ProxyException, self).__init__(message)


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
        super(ClientHandshakeException, self).__init__(message)
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
