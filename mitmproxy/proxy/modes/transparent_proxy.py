from mitmproxy import exceptions
from mitmproxy import platform
from mitmproxy.proxy import protocol


class TransparentProxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __init__(self, ctx):
        super().__init__(ctx)

    def __call__(self):
        try:
            self.server_conn.address = platform.original_addr(self.client_conn.connection)
        except Exception as e:
            raise exceptions.ProtocolException("Transparent mode failure: %s" % repr(e))

        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn.connected():
                self.disconnect()
