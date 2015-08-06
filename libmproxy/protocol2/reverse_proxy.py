from __future__ import (absolute_import, print_function, division)

from .layer import Layer, ServerConnectionMixin
from .ssl import SslLayer


class ReverseProxy(Layer, ServerConnectionMixin):

    def __init__(self, ctx, server_address, client_ssl, server_ssl):
        super(ReverseProxy, self).__init__(ctx)
        self.server_address = server_address
        self.client_ssl = client_ssl
        self.server_ssl = server_ssl

    def __call__(self):
        layer = SslLayer(self, self.client_ssl, self.server_ssl)
        for message in layer():
            if not self._handle_server_message(message):
                yield message
