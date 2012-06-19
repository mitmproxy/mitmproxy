from netlib import tcp, protocol, odict, wsgi
import version, app


class PathodHandler(tcp.BaseHandler):
    def handle(self):
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            return None

        method, path, httpversion = protocol.parse_init_http(line)
        headers = odict.ODictCaseless(protocol.read_headers(self.rfile))
        content = protocol.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, None
                )
        cc = wsgi.ClientConn(self.client_address)
        req = wsgi.Request(cc, "http", method, path, headers, content)
        sn = self.connection.getsockname()
        app = wsgi.WSGIAdaptor(
            self.server.app,
            sn[0],
            self.server.port,
            version.NAMEVERSION
        )
        app.serve(req, self.wfile)



class Pathod(tcp.TCPServer):
    def __init__(self, addr):
        tcp.TCPServer.__init__(self, addr)
        self.app = app.app
        self.app.config["pathod"] = self

    def handle_connection(self, request, client_address):
        PathodHandler(request, client_address, self)
