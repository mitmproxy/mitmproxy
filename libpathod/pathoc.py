from netlib import tcp, http
import rparse

class PathocError(Exception): pass


class Pathoc(tcp.TCPClient):
    def __init__(self, ssl, host, port, clientcert):
        try:
            tcp.TCPClient.__init__(self, ssl, host, port, clientcert)
        except tcp.NetLibError, v:
            raise PathocError(v)

    def request(self, spec):
        r = rparse.parse_request({}, spec)
        r.serve(self.wfile)
        self.wfile.flush()

        line = self.rfile.readline()
        print line

