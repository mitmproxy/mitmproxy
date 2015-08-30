from __future__ import (absolute_import, print_function, division)

from ..protocol2.layer import Layer, ServerConnectionMixin


class HttpUpstreamProxy(Layer, ServerConnectionMixin):
    def __init__(self, ctx, server_address):
        super(HttpUpstreamProxy, self).__init__(ctx, server_address=server_address)

    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn:
                self._disconnect()
