from __future__ import (absolute_import, print_function, division)

from .layer import Layer, ServerConnectionMixin
#from .http import HttpLayer


class UpstreamProxy(Layer, ServerConnectionMixin):

    def __init__(self, ctx, server_address):
        super(UpstreamProxy, self).__init__(ctx)
        self.server_address = server_address

    def __call__(self):
        #layer = HttpLayer(self)
        layer = None
        for message in layer():
            if not self._handle_server_message(message):
                yield message
