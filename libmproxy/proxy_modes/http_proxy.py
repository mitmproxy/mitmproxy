from __future__ import (absolute_import, print_function, division)

from ..protocol2.layer import Layer, ServerConnectionMixin


class HttpProxy(Layer, ServerConnectionMixin):
    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn:
                self._disconnect()
