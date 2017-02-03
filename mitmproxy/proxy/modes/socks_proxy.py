from mitmproxy import exceptions
from mitmproxy.proxy import protocol
from mitmproxy.net import socks


class Socks5Proxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __call__(self):
        try:
            # Parse Client Greeting
            client_greet = socks.ClientGreeting.from_file(self.client_conn.rfile, fail_early=True)
            client_greet.assert_socks5()
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
            server_greet.to_file(self.client_conn.wfile)
            self.client_conn.wfile.flush()

            # Parse Connect Request
            connect_request = socks.Message.from_file(self.client_conn.rfile)
            connect_request.assert_socks5()
            if connect_request.msg != socks.CMD.CONNECT:
                raise socks.SocksError(
                    socks.REP.COMMAND_NOT_SUPPORTED,
                    "mitmproxy only supports SOCKS5 CONNECT"
                )

            # We always connect lazily, but we need to pretend to the client that we connected.
            connect_reply = socks.Message(
                socks.VERSION.SOCKS5,
                socks.REP.SUCCEEDED,
                connect_request.atyp,
                # dummy value, we don't have an upstream connection yet.
                connect_request.addr
            )
            connect_reply.to_file(self.client_conn.wfile)
            self.client_conn.wfile.flush()

        except (socks.SocksError, exceptions.TcpException) as e:
            raise exceptions.Socks5ProtocolException("SOCKS5 mode failure: %s" % repr(e))

        self.server_conn.address = connect_request.addr

        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn.connected():
                self.disconnect()
