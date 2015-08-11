from __future__ import (absolute_import, print_function, division)

from ..exceptions import ProtocolException
from ..proxy import ProxyError, Socks5ProxyMode
from .layer import Layer, ServerConnectionMixin


class Socks5Proxy(Layer, ServerConnectionMixin):
    def __call__(self):
        try:
            s5mode = Socks5ProxyMode(self.config.ssl_ports)
            address = s5mode.get_upstream_server(self.client_conn)[2:]
        except ProxyError as e:
            # TODO: Unmonkeypatch
            raise ProtocolException(str(e), e)

        self.server_address = address

        layer = self.ctx.next_layer(self)
        for message in layer():
            if not self._handle_server_message(message):
                yield message
