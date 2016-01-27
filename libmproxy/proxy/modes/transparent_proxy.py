from __future__ import (absolute_import, print_function, division)

from ... import platform
from ...exceptions import ProtocolException
from ...protocol import Layer, ServerConnectionMixin


class TransparentProxy(Layer, ServerConnectionMixin):

    def __init__(self, ctx):
        super(TransparentProxy, self).__init__(ctx)
        self.resolver = platform.resolver()

    def __call__(self):
        try:
            self.server_conn.address = self.resolver.original_addr(self.client_conn.connection)
        except Exception as e:
            raise ProtocolException("Transparent mode failure: %s" % repr(e))

        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn:
                self.disconnect()
