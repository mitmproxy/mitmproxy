from __future__ import (absolute_import, print_function, division)

from .layer import Layer, ServerConnectionMixin
from .http import HttpLayer


class HttpProxy(Layer, ServerConnectionMixin):
    def __call__(self):
        layer = HttpLayer(self, "regular")
        for message in layer():
            if not self._handle_server_message(message):
                yield message


class HttpUpstreamProxy(Layer, ServerConnectionMixin):
    def __init__(self, ctx, server_address):
        super(HttpUpstreamProxy, self).__init__(ctx)
        self.server_address = server_address

    def __call__(self):
        layer = HttpLayer(self, "upstream")
        for message in layer():
            if not self._handle_server_message(message):
                yield message
