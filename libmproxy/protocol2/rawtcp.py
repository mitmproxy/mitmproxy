from __future__ import (absolute_import, print_function, division, unicode_literals)
from ..protocol.tcp import TCPHandler
from .layer import Layer
from .messages import Connect


class TcpLayer(Layer):
    def __call__(self):
        yield Connect()
        tcp_handler = TCPHandler(self)
        tcp_handler.handle_messages()

    def establish_server_connection(self):
        pass
        # FIXME: Remove method, currently just here to mock TCPHandler's call to it.
