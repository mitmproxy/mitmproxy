from BaseHTTPServer import HTTPServer
import handler

def make(port):
    server_address = ('127.0.0.1', port)
    return HTTPServer(server_address, handler.TestRequestHandler)
