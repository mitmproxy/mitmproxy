"""
We try to be very hygienic regarding the exceptions we throw:
Every Exception mitmproxy raises shall be a subclass of ProxyException.


See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""
from __future__ import (absolute_import, print_function, division)


class ProxyException(Exception):
    """
    Base class for all exceptions thrown by libmproxy.

    Args:
        message: the error message
        cause: (optional) an error object that caused this exception, e.g. an IOError.
    """
    def __init__(self, message, cause=None):
        """
        :param message: Error Message
        :param cause: Exception object that caused this exception to be thrown.
        """
        super(ProxyException, self).__init__(message)
        self.cause = cause


class ProtocolException(ProxyException):
    pass


class TlsException(ProtocolException):
    pass


class Socks5Exception(ProtocolException):
    pass


class HttpException(ProtocolException):
    pass


class InvalidCredentials(HttpException):
    pass


class ServerException(ProxyException):
    pass
