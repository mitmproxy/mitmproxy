from mitmproxy.proxy import protocol


class HttpProxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn.connected():
                self.disconnect()


class HttpUpstreamProxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __init__(self, ctx, server_address):
        super().__init__(ctx, server_address=server_address)

    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn.connected():
                self.disconnect()
