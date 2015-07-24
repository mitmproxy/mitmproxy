from . import Layer, Connect
from ..protocol.tcp import TCPHandler


class TcpLayer(Layer):
    def __call__(self):
        yield Connect()
        tcp_handler = TCPHandler(self)
        tcp_handler.handle_messages()

    def establish_server_connection(self):
        pass
        # FIXME: Remove method, currently just here to mock TCPHandler's call to it.
