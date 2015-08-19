from __future__ import (absolute_import, print_function, division)

from ..exceptions import ProtocolException
from .. import platform
from .layer import Layer, ServerConnectionMixin


class TransparentProxy(Layer, ServerConnectionMixin):

    def __init__(self, ctx):
        super(TransparentProxy, self).__init__(ctx)
        self.resolver = platform.resolver()

    def __call__(self):
        try:
            self.server_conn.address = self.resolver.original_addr(self.client_conn.connection)
        except Exception as e:
            raise ProtocolException("Transparent mode failure: %s" % repr(e), e)

        layer = self.ctx.next_layer(self)
        for message in layer():
            if not self._handle_server_message(message):
                yield message
