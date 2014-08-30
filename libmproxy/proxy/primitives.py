from __future__ import absolute_import


class ProxyError(Exception):
    def __init__(self, code, message, headers=None):
        super(ProxyError, self).__init__(self, message)
        self.code, self.headers = code, headers


class ProxyServerError(Exception):
    pass


class UpstreamServerResolver(object):
    def __call__(self, conn):
        """
        Returns the address of the server to connect to.
        """
        raise NotImplementedError  # pragma: nocover


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
        try:
            dst = self.resolver.original_addr(conn)
        except Exception, e:
            raise ProxyError(502, "Transparent mode failure: %s" % str(e))

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
    """upstream server from arguments (reverse proxy, upstream proxy or from transparent resolver)"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""


class Log:
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level