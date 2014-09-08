from __future__ import absolute_import


class ProxyError(Exception):
    def __init__(self, code, message, headers=None):
        super(ProxyError, self).__init__(message)
        self.code, self.headers = code, headers


class ProxyServerError(Exception):
    pass


class ProxyMode(object):
    http_form_in = None
    http_form_out = None

    def get_upstream_server(self, conn):
        """
        Returns the address of the server to connect to.
        Returns None if the address needs to be determined on the protocol level (regular proxy mode)
        """
        raise NotImplementedError()  # pragma: nocover

    @property
    def name(self):
        return self.__class__.__name__.replace("ProxyMode", "").lower()

    def __str__(self):
        return self.name

    def __eq__(self, other):
        """
        Allow comparisions with "regular" etc.
        """
        if isinstance(other, ProxyMode):
            return self is other
        else:
            return self.name == other

    def __ne__(self, other):
        return not self.__eq__(other)


class RegularProxyMode(ProxyMode):
    http_form_in = "absolute"
    http_form_out = "relative"

    def get_upstream_server(self, conn):
        return None


class TransparentProxyMode(ProxyMode):
    http_form_in = "relative"
    http_form_out = "relative"

    def __init__(self, resolver, sslports):
        self.resolver = resolver
        self.sslports = sslports

    def get_upstream_server(self, conn):
        try:
            dst = self.resolver.original_addr(conn)
        except Exception, e:
            raise ProxyError(502, "Transparent mode failure: %s" % str(e))

        if dst[1] in self.sslports:
            ssl = True
        else:
            ssl = False
        return [ssl, ssl] + list(dst)


class _ConstDestinationProxyMode(ProxyMode):
    def __init__(self, dst):
        self.dst = dst

    def get_upstream_server(self, conn):
        return self.dst


class ReverseProxyMode(_ConstDestinationProxyMode):
    http_form_in = "relative"
    http_form_out = "relative"


class UpstreamProxyMode(_ConstDestinationProxyMode):
    http_form_in = "absolute"
    http_form_out = "absolute"


class Log:
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level