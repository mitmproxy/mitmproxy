from __future__ import absolute_import
from netlib import socks

class ProxyError(Exception):
    def __init__(self, code, message, headers=None):
        super(ProxyError, self).__init__(message)
        self.code, self.headers = code, headers


class ProxyServerError(Exception):
    pass


class ProxyMode(object):
    http_form_in = None
    http_form_out = None

    def get_upstream_server(self, client_conn):
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

    def get_upstream_server(self, client_conn):
        return None


class TransparentProxyMode(ProxyMode):
    http_form_in = "relative"
    http_form_out = "relative"

    def __init__(self, resolver, sslports):
        self.resolver = resolver
        self.sslports = sslports

    def get_upstream_server(self, client_conn):
        try:
            dst = self.resolver.original_addr(client_conn.connection)
        except Exception, e:
            raise ProxyError(502, "Transparent mode failure: %s" % str(e))

        if dst[1] in self.sslports:
            ssl = True
        else:
            ssl = False
        return [ssl, ssl] + list(dst)


class Socks5ProxyMode(ProxyMode):
    http_form_in = "relative"
    http_form_out = "relative"

    def __init__(self, sslports):
        self.sslports = sslports

    @staticmethod
    def _assert_socks5(msg):
        if msg.ver != socks.VERSION.SOCKS5:
            if msg.ver == ord("G") and len(msg.methods) == ord("E"):
                guess = "Probably not a SOCKS request but a regular HTTP request. "
            else:
                guess = ""
            raise socks.SocksError(
                socks.REP.GENERAL_SOCKS_SERVER_FAILURE,
                guess + "Invalid SOCKS version. Expected 0x05, got 0x%x" % msg.ver)

    def get_upstream_server(self, client_conn):
        try:
            # Parse Client Greeting
            client_greet = socks.ClientGreeting.from_file(client_conn.rfile)
            self._assert_socks5(client_greet)
            if socks.METHOD.NO_AUTHENTICATION_REQUIRED not in client_greet.methods:
                raise socks.SocksError(
                    socks.METHOD.NO_ACCEPTABLE_METHODS,
                    "mitmproxy only supports SOCKS without authentication"
                )

            # Send Server Greeting
            server_greet = socks.ServerGreeting(
                socks.VERSION.SOCKS5,
                socks.METHOD.NO_AUTHENTICATION_REQUIRED
            )
            server_greet.to_file(client_conn.wfile)
            client_conn.wfile.flush()

            # Parse Connect Request
            connect_request = socks.Message.from_file(client_conn.rfile)
            self._assert_socks5(connect_request)
            if connect_request.msg != socks.CMD.CONNECT:
                raise socks.SocksError(
                    socks.REP.COMMAND_NOT_SUPPORTED,
                    "mitmproxy only supports SOCKS5 CONNECT."
                )

            # We do not connect here yet, as the clientconnect event has not been handled yet.

            connect_reply = socks.Message(
                socks.VERSION.SOCKS5,
                socks.REP.SUCCEEDED,
                socks.ATYP.DOMAINNAME,
                client_conn.address  # dummy value, we don't have an upstream connection yet.
            )
            connect_reply.to_file(client_conn.wfile)
            client_conn.wfile.flush()

            ssl = bool(connect_request.addr.port in self.sslports)
            return ssl, ssl, connect_request.addr.host, connect_request.addr.port

        except socks.SocksError as e:
            msg = socks.Message(5, e.code, socks.ATYP.DOMAINNAME, repr(e))
            try:
                msg.to_file(client_conn.wfile)
            except:
                pass
            raise ProxyError(502, "SOCKS5 mode failure: %s" % str(e))


class _ConstDestinationProxyMode(ProxyMode):
    def __init__(self, dst):
        self.dst = dst

    def get_upstream_server(self, client_conn):
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