import sys, os
from netlib import tcp, http
import rparse, utils

class PathocError(Exception): pass


def print_short(fp, httpversion, code, msg, headers, content):
    print >> fp, "<< %s %s: %s bytes"%(code, utils.xrepr(msg), len(content))


def print_full(fp, httpversion, code, msg, headers, content):
    print >> fp, "<< HTTP%s/%s %s %s"%(httpversion[0], httpversion[1], code, utils.xrepr(msg))
    print >> fp, utils.escape_unprintables(str(headers))
    print >> fp, utils.escape_unprintables(content)


class Pathoc(tcp.TCPClient):
    def __init__(self, host, port):
        tcp.TCPClient.__init__(self, host, port)
        self.settings = dict(
            staticdir = os.getcwd(),
            unconstrained_file_access = True,
        )

    def request(self, spec):
        """
            Return an (httpversion, code, msg, headers, content) tuple.

            May raise rparse.ParseException, netlib.http.HttpError or
            rparse.FileAccessDenied.
        """
        r = rparse.parse_request(self.settings, spec)
        ret = r.serve(self.wfile, None, self.host)
        self.wfile.flush()
        return http.read_response(self.rfile, r.method, None)

    def print_requests(self, reqs, respdump, reqdump, fp=sys.stdout):
        """
            Performs a series of requests, and prints results to the specified
            file pointer.
        """
        for i in reqs:
            try:
                r = rparse.parse_request(self.settings, i)
                req = r.serve(self.wfile, None, self.host)
                if reqdump:
                    print >> fp, "\n>>", req["method"], repr(req["path"])
                    for a in req["actions"]:
                        print >> fp, "\t",
                        for x in a:
                            print >> fp, x,
                        print >> fp
                self.wfile.flush()
                resp = http.read_response(self.rfile, r.method, None)
            except rparse.ParseException, v:
                print >> fp, "Error parsing request spec: %s"%v.msg
                print >> fp, v.marked()
                return
            except rparse.FileAccessDenied, v:
                print >> fp, "File access error: %s"%v
                return
            except http.HttpError, v:
                print >> fp, "<<", v.msg
                return
            except tcp.NetLibTimeout:
                print >> fp, "<<", "Timeout"
                return
            except tcp.NetLibDisconnect: # pragma: nocover
                print >> fp, "<<", "Disconnect"
                return
            else:
                if respdump:
                    print_full(fp, *resp)
                else:
                    print_short(fp, *resp)
