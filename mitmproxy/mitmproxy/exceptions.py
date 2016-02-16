"""
We try to be very hygienic regarding the exceptions we throw:
Every Exception mitmproxy raises shall be a subclass of ProxyException.


See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""
from __future__ import (absolute_import, print_function, division)


class ProxyException(Exception):

    """
    Base class for all exceptions thrown by mitmproxy.
    """

    def __init__(self, message=None):
        super(ProxyException, self).__init__(message)


class ProtocolException(ProxyException):
    pass


class TlsProtocolException(ProtocolException):
    pass


class ClientHandshakeException(TlsProtocolException):

    def __init__(self, message, server):
        super(ClientHandshakeException, self).__init__(message)
        self.server = server


class Socks5ProtocolException(ProtocolException):
    pass


class HttpProtocolException(ProtocolException):
    pass


class ServerException(ProxyException):
    pass


class ContentViewException(ProxyException):
    pass


class ReplayException(ProxyException):
    pass


class ScriptException(ProxyException):
    pass
