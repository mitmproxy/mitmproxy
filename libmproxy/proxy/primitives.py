from __future__ import absolute_import

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


class UpstreamServerResolver(object):
    def __call__(self, conn):
        """
        Returns the address of the server to connect to.
        """
        raise NotImplementedError


class ConstUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, dst):
        self.dst = dst

    def __call__(self, conn):
        return self.dst


class TransparentUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, resolver, sslports):
        self.resolver = resolver
        self.sslports = sslports

    def __call__(self, conn):
        dst = self.resolver.original_addr(conn)
        if not dst:
            raise ProxyError(502, "Transparent mode failure: could not resolve original destination.")

        if dst[1] in self.sslports:
            ssl = True
        else:
            ssl = False
        return [ssl, ssl] + list(dst)


class AddressPriority(object):
    """
    Enum that signifies the priority of the given address when choosing the destination host.
    Higher is better (None < i)
    """
    MANUALLY_CHANGED = 3
    """user changed the target address in the ui"""
    FROM_SETTINGS = 2
    """upstream server from arguments (reverse proxy, forward proxy or from transparent resolver)"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""


class Log:
    def __init__(self, msg):
        self.msg = msg