from netlib import tcp, http
import rparse

class PathocError(Exception): pass


def print_short(fp, httpversion, code, msg, headers, content):
    print >> fp, "%s %s: %s bytes"%(code, msg, len(content))


def print_full(fp, httpversion, code, msg, headers, content):
    print >> fp, "HTTP%s/%s %s %s"%(httpversion[0], httpversion[1], code, msg)
    print >> fp, headers
    print >> fp, content


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
        return http.read_response(self.rfile, r.method, None)
