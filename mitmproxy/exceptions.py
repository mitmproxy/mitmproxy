"""

Edit 2020-12 @mhils:
    The advice below hasn't paid off in any form. We now just use builtin exceptions and specialize where necessary.

---

We try to be very hygienic regarding the exceptions we throw:

- Every exception that might be externally visible to users shall be a subclass
  of MitmproxyException.p
- Every exception in the base net module shall be a subclass
  of NetlibException, and will not be propagated directly to users.

See also: http://lucumr.pocoo.org/2014/10/16/on-error-handling/
"""


class MitmproxyException(Exception):
    """
    Base class for all exceptions thrown by mitmproxy.
    """

    def __init__(self, message=None):
        super().__init__(message)


class Kill(MitmproxyException):
    """
    Signal that both client and server connection(s) should be killed immediately.
    """
    pass


class ContentViewException(MitmproxyException):
    pass


class ReplayException(MitmproxyException):
    pass


class FlowReadException(MitmproxyException):
    pass


class ControlException(MitmproxyException):
    pass


class CommandError(Exception):
    pass


class OptionsError(MitmproxyException):
    pass


class AddonManagerError(MitmproxyException):
    pass


class AddonHalt(MitmproxyException):
    """
        Raised by addons to signal that no further handlers should handle this event.
    """
    pass


class TypeError(MitmproxyException):
    pass


class NetlibException(MitmproxyException):
    """
    Base class for all exceptions thrown by mitmproxy.net.
    """

    def __init__(self, message=None):
        super().__init__(message)


class HttpException(NetlibException):
    pass


class HttpSyntaxException(HttpException):
    pass


class TlsException(NetlibException):
    pass
