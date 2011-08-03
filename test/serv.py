import socket
from SocketServer import BaseServer
from BaseHTTPServer import HTTPServer
import handler

def make(port):
    server_address = ('', port)
    return HTTPServer(server_address, handler.TestRequestHandler)


