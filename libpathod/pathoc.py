import sys
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
    def __init__(self, host, port):
        tcp.TCPClient.__init__(self, host, port)

    def request(self, spec):
        """
            Return an (httpversion, code, msg, headers, content) tuple.

            May raise rparse.ParseException and netlib.http.HttpError.
        """
        r = rparse.parse_request({}, spec)
        r.serve(self.wfile)
        self.wfile.flush()
        return http.read_response(self.rfile, r.method, None)

    def print_requests(self, reqs, verbose, fp=sys.stdout):
        """
            Performs a series of requests, and prints results to the specified
            file pointer.
        """
        for i in reqs:
            try:
                ret = self.request(i)
            except rparse.ParseException, v:
                print >> fp, "Error parsing request spec: %s"%v.msg
                print >> fp, v.marked()
                return
            except http.HttpError, v:
                print >> fp, v.msg
                return
            except tcp.NetLibTimeout:
                print >> fp, "Timeout"
            else:
                if verbose:
                    print_full(fp, *ret)
                else:
                    print_short(fp, *ret)
