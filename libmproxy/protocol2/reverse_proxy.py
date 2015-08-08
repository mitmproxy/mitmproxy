from __future__ import (absolute_import, print_function, division)

from .layer import Layer, ServerConnectionMixin
from .tls import TlsLayer


class ReverseProxy(Layer, ServerConnectionMixin):

    def __init__(self, ctx, server_address, client_tls, server_tls):
        super(ReverseProxy, self).__init__(ctx)
        self.server_address = server_address
        self._client_tls = client_tls
        self._server_tls = server_tls

    def __call__(self):
        layer = TlsLayer(self, self._client_tls, self._server_tls)
        for message in layer():
            if not self._handle_server_message(message):
                yield message
