#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import urlparse

class S(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = urlparse.parse_qs(self.rfile.read(length))
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(40))
        self.end_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")
        self.wfile.flush()
        
def run(server_class=HTTPServer, handler_class=S, port=1234):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd on port %d...' % port
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
