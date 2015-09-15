"""
We try to be very hygienic regarding the exceptions we throw:
Every Exception netlib raises shall be a subclass of NetlibException.


See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""
from __future__ import absolute_import, print_function, division


class NetlibException(Exception):
    """
    Base class for all exceptions thrown by netlib.
    """
    def __init__(self, message=None):
        super(NetlibException, self).__init__(message)


class ReadDisconnect(object):
    """Immediate EOF"""


class HttpException(NetlibException):
    pass


class HttpReadDisconnect(HttpException, ReadDisconnect):
    pass

class HttpSyntaxException(HttpException):
    pass
