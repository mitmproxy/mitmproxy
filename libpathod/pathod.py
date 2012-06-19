from netlib import tcp, protocol, odict

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
        print method, path, httpversion
        #return flow.Request(client_conn, httpversion, host, port, "http", method, path, headers, content)


class Pathod(tcp.TCPServer):
    def __init__(self, addr):
        tcp.TCPServer.__init__(self, addr)

    def handle_connection(self, request, client_address):
        PathodHandler(request, client_address, self)
