from libmproxy.proxy import ProxyError, ConnectionHandler
from netlib import http

def handle_messages(conntype, connection_handler):
    handler = None
    if conntype == "http":
        handler = HTTPHandler(connection_handler)
    else:
        raise NotImplementedError

    return handler.handle_messages()


class ProtocolHandler(object):
    def __init__(self, c):
        self.c = c

class HTTPHandler(ProtocolHandler):

    def handle_messages(self):
        while self.handle_request():
            pass
        self.c.close = True

    def handle_request(self):
        request = self.read_request()
        if request is None:
            return
        raise NotImplementedError

    def read_request(self):
        self.c.client_conn.rfile.reset_timestamps()

        request_line = self.get_line(self.c.client_conn.rfile)
        method, path, httpversion = http.parse_init(request_line)
        headers = self.read_headers(authenticate=True)

        if self.mode == "regular":
            if method == "CONNECT":
                r = http.parse_init_connect(request_line)
                if not r:
                    raise ProxyError(400, "Bad HTTP request line: %s"%repr(request_line))
                host, port, _ = r
                if self.config.forward_proxy:
                    self.server_conn.wfile.write(request_line)
                    for key, value in headers.items():
                        self.server_conn.wfile.write("%s: %s\r\n"%(key, value))
                    self.server_conn.wfile.write("\r\n")
                else:
                    self.server_address = (host, port)
                    self.establish_server_connection()

                self.handle_ssl()
                self.mode = "transparent"
                return
            else:
                r = http.parse_init_proxy(request_line)
                if not r:
                    raise ProxyError(400, "Bad HTTP request line: %s"%repr(request_line))
                method, scheme, host, port, path, httpversion = r
                if not self.config.forward_proxy:
                    if (not self.server_conn) or (self.server_address != (host, port)):
                        self.server_address = (host, port)
                        self.establish_server_connection()

    def get_line(self, fp):
        """
            Get a line, possibly preceded by a blank.
        """
        line = fp.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = fp.readline()
        return line

    def read_headers(self, authenticate=False):
        headers = http.read_headers(self.client_conn.rfile)
        if headers is None:
            raise ProxyError(400, "Invalid headers")
        if authenticate and self.config.authenticator:
            if self.config.authenticator.authenticate(headers):
                self.config.authenticator.clean(headers)
            else:
                raise ProxyError(
                            407,
                            "Proxy Authentication Required",
                            self.config.authenticator.auth_challenge_headers()
                       )
        return headers