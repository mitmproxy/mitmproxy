from __future__ import absolute_import
from netlib import socks, tcp


class ProxyError(Exception):
    def __init__(self, code, message, headers=None):
        super(ProxyError, self).__init__(self, message)
        self.code, self.headers = code, headers

class ConnectionTypeChange(Exception):
    """
    Gets raised if the connection type has been changed (e.g. after HTTP/1.1 101 Switching Protocols).
    It's up to the raising ProtocolHandler to specify the new conntype before raising the exception.
    """
    pass


class ProxyServerError(Exception):
    pass


class UpstreamServerResolver(object):
    def __call__(self, conn_handler):
        """
        Returns the address of the server to connect to.
        """
        raise NotImplementedError  # pragma: nocover


class SocksUpstreamServerResolver(UpstreamServerResolver):

    def __init__(self, sslports):
        self.sslports = sslports

    def _assert_socks5(self, msg):
        if msg.ver != 0x05:
            raise socks.SocksError(
                socks.REP.GENERAL_SOCKS_SERVER_FAILURE,
                "Invalid SOCKS version. Expected 0x05, got %x" % msg.ver)

    def __call__(self, conn_handler):
        try:
            client_greet = socks.ClientGreeting.from_file(conn_handler.client_conn.rfile)
            self._assert_socks5(client_greet)
            if 0x00 not in client_greet.methods:
                raise socks.SocksError(
                    socks.METHOD.NO_ACCEPTABLE_METHODS,
                    "mitmproxy only supports SOCKS without authentication"
                )
            server_greet = socks.ServerGreeting(0x05, socks.METHOD.NO_AUTHENTICATION_REQUIRED)
            server_greet.to_file(conn_handler.client_conn.wfile)
            conn_handler.client_conn.wfile.flush()

            connect_request = socks.Message.from_file(conn_handler.client_conn.rfile)
            self._assert_socks5(connect_request)
            if connect_request.msg != 0x01:
                raise socks.SocksError(
                    socks.REP.COMMAND_NOT_SUPPORTED,
                    "mitmproxy only supports SOCKS5 CONNECT."
                )

            try:
                conn_handler.set_server_address(connect_request.addr, AddressPriority.FROM_SETTINGS)
                conn_handler.establish_server_connection()
            except ProxyError, e:
                raise socks.SocksError(socks.REP.GENERAL_SOCKS_SERVER_FAILURE, e.message)

            connect_reply = socks.Message(0x05,
                                          socks.REP.SUCCEEDED,
                                          connect_request.atyp,
                                          tcp.Address.wrap(conn_handler.server_conn.sockname[:2]))
            connect_reply.to_file(conn_handler.client_conn.wfile)
            conn_handler.client_conn.wfile.flush()
            ssl = (connect_request.addr.port in self.sslports)
            return (ssl, ssl, connect_request.addr.host, connect_request.addr.port)
        except socks.SocksError, e:
            msg = socks.Message(5, e.code, socks.ATYP.DOMAINNAME, repr(e))
            try:
                msg.to_file(conn_handler.client_conn.wfile)
            except:
                pass
            raise e


class ConstUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, dst):
        self.dst = dst

    def __call__(self, conn_handler):
        return self.dst


class TransparentUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, resolver, sslports):
        self.resolver = resolver
        self.sslports = sslports

    def __call__(self, conn_handler):
        dst = self.resolver.original_addr(conn_handler.client_conn.connection)
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
    """upstream server from arguments (reverse proxy, upstream proxy or from transparent resolver)"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""


class Log:
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level