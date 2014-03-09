class ProxyError(Exception):
    def __init__(self, code, msg, headers=None):
        self.code, self.msg, self.headers = code, msg, headers

    def __str__(self):
        return "ProxyError(%s, %s)" % (self.code, self.msg)


class ConnectionTypeChange(Exception):
    """
    Gets raised if the connection type has been changed (e.g. after HTTP/1.1 101 Switching Protocols).
    It's up to the raising ProtocolHandler to specify the new conntype before raising the exception.
    """
    pass


class ProxyServerError(Exception):
    pass


class AddressPriority(object):
    """
    Enum that signifies the priority of the given address when choosing the destination host.
    Higher is better (None < i)
    """
    FORCE = 5
    """forward mode"""
    MANUALLY_CHANGED = 4
    """user changed the target address in the ui"""
    FROM_SETTINGS = 3
    """reverse proxy mode"""
    FROM_CONNECTION = 2
    """derived from transparent resolver"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""


class Log:
    def __init__(self, msg):
        self.msg = msg