import socket
from SocketServer import BaseServer
from BaseHTTPServer import HTTPServer
import ssl
import handler


class SecureHTTPServer(HTTPServer):
    def __init__(self, server_address, HandlerClass):
        BaseServer.__init__(self, server_address, HandlerClass)
        self.socket = ssl.wrap_socket(
                            socket.socket(self.address_family, self.socket_type),
                            keyfile = "data/serverkey.pem",
                            certfile = "data/serverkey.pem"
                      )
        self.server_bind()
        self.server_activate()


def make(port):
    server_address = ('', port)
    return SecureHTTPServer(server_address, handler.TestRequestHandler)
