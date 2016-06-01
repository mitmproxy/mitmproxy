from __future__ import absolute_import, print_function, division

from mitmproxy import protocol


class ReverseProxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __init__(self, ctx, server_address, server_tls):
        super(ReverseProxy, self).__init__(ctx, server_address=server_address)
        self.server_tls = server_tls

    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn:
                self.disconnect()
