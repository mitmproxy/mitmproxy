from __future__ import (absolute_import, print_function, division, unicode_literals)

from ..proxy import ProxyError, Socks5ProxyMode, ProxyError2
from . import Layer, ServerConnectionMixin
from .rawtcp import TcpLayer
from .ssl import SslLayer


class Socks5IncomingLayer(Layer, ServerConnectionMixin):
    def __call__(self):
        try:
            s5mode = Socks5ProxyMode(self.config.ssl_ports)
            address = s5mode.get_upstream_server(self.client_conn)[2:]
        except ProxyError as e:
            # TODO: Unmonkeypatch
            raise ProxyError2(str(e), e)

        self._set_address(address)

        if address[1] == 443:
            layer = SslLayer(self, True, True)
        else:
            layer = TcpLayer(self)
        for message in layer():
            if not self._handle_server_message(message):
                yield message
