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