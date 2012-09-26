import sys, os
from netlib import tcp, http
import netlib.utils
import rparse, utils

class PathocError(Exception): pass


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

    def _show_summary(self, fp, httpversion, code, msg, headers, content):
        print >> fp, "<< %s %s: %s bytes"%(code, utils.xrepr(msg), len(content))

    def _show(self, fp, header, data, hexdump):
        if hexdump:
            print >> fp, "%s (hex dump):"%header
            for line in netlib.utils.hexdump(data):
                print >> fp, "\t%s %s %s"%line
        else:
            print >> fp, "%s (unprintables escaped):"%header
            print >> fp, netlib.utils.cleanBin(data)

    def print_request(self, spec, showreq, showresp, explain, hexdump, ignorecodes, fp=sys.stdout):
        """
            Performs a series of requests, and prints results to the specified
            file descriptor.

            spec: A request specification
            showreq: Print requests
            showresp: Print responses
            explain: Print request explanation
            hexdump: When printing requests or responses, use hex dump output
            ignorecodes: Sequence of return codes to ignore
        """
        try:
            r = rparse.parse_request(self.settings, spec)
        except rparse.ParseException, v:
            print >> fp, "Error parsing request spec: %s"%v.msg
            print >> fp, v.marked()
            return
        except rparse.FileAccessDenied, v:
            print >> fp, "File access error: %s"%v
            return

        resp, req = None, None
        if showreq:
            self.wfile.start_log()
        try:
            req = r.serve(self.wfile, None, self.host)
            self.wfile.flush()
            if showresp:
                self.rfile.start_log()
            resp = http.read_response(self.rfile, r.method, None)
        except http.HttpError, v:
            print >> fp, "<< HTTP Error:", v.msg
        except tcp.NetLibTimeout:
            print >> fp, "<<", "Timeout"
        except tcp.NetLibDisconnect: # pragma: nocover
            print >> fp, "<<", "Disconnect"

        if req:
            if ignorecodes and resp and resp[1] in ignorecodes:
                return
            if explain:
                print >> fp, ">>", req["method"], repr(req["path"])
                for a in req["actions"]:
                    print >> fp, "\t",
                    for x in a:
                        print >> fp, x,
                    print >> fp
            if showreq:
                self._show(fp, ">> Request", self.wfile.get_log(), hexdump)

            if showresp:
                self._show(fp, "<< Response", self.rfile.get_log(), hexdump)
            else:
                if resp:
                    self._show_summary(fp, *resp)
