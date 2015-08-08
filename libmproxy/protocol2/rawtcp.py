from __future__ import (absolute_import, print_function, division)
import OpenSSL
from ..exceptions import ProtocolException
from ..protocol.tcp import TCPHandler
from .layer import Layer
from .messages import Connect


class TcpLayer(Layer):
    def __call__(self):
        yield Connect()
        tcp_handler = TCPHandler(self)
        try:
            tcp_handler.handle_messages()
        except OpenSSL.SSL.Error as e:
            raise ProtocolException("SSL error: %s" % repr(e), e)


    def establish_server_connection(self):
        pass
        # FIXME: Remove method, currently just here to mock TCPHandler's call to it.
