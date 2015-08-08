from __future__ import (absolute_import, print_function, division)


class ProxyException(Exception):
    """
    Base class for all exceptions thrown by libmproxy.
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


class ServerException(ProxyException):
    pass