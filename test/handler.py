import socket
from BaseHTTPServer import BaseHTTPRequestHandler


class TestRequestHandler(BaseHTTPRequestHandler):
    default_request_version = "HTTP/1.1"
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def log_message(self, *args, **kwargs):
        # Silence output
        pass

    def do_GET(self):
        data = "data: %s\npath: %s\n"%(self.headers, self.path)
        self.send_response(200)
        self.send_header("proxtest", "testing")
        self.send_header("Content-type", "text-html")
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

