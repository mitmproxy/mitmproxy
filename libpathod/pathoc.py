import sys
import os
import hashlib
import random
import time

import OpenSSL.crypto

from netlib import tcp, http, certutils
import netlib.utils

import language
import utils


class PathocError(Exception):
    pass


class SSLInfo:
    def __init__(self, certchain, cipher):
        self.certchain, self.cipher = certchain, cipher

    def __str__(self):
        parts = [
            "Cipher: %s, %s bit, %s"%self.cipher,
            "SSL certificate chain:"
        ]
        for i in self.certchain:
            parts.append("\tSubject: ")
            for cn in i.get_subject().get_components():
                parts.append("\t\t%s=%s"%cn)
            parts.append("\tIssuer: ")
            for cn in i.get_issuer().get_components():
                parts.append("\t\t%s=%s"%cn)
            parts.extend(
                [
                    "\tVersion: %s"%i.get_version(),
                    "\tValidity: %s - %s"%(
                        i.get_notBefore(), i.get_notAfter()
                    ),
                    "\tSerial: %s"%i.get_serial_number(),
                    "\tAlgorithm: %s"%i.get_signature_algorithm()
                ]
            )
            pk = i.get_pubkey()
            types = {
                OpenSSL.crypto.TYPE_RSA: "RSA",
                OpenSSL.crypto.TYPE_DSA: "DSA"
            }
            t = types.get(pk.type(), "Uknown")
            parts.append("\tPubkey: %s bit %s"%(pk.bits(), t))
            s = certutils.SSLCert(i)
            if s.altnames:
                parts.append("\tSANs: %s"%" ".join(s.altnames))
            return "\n".join(parts)


class Response:
    def __init__(
        self,
        httpversion,
        status_code,
        msg,
        headers,
        content,
        sslinfo
    ):
        self.httpversion, self.status_code = httpversion, status_code
        self.msg = msg
        self.headers, self.content = headers, content
        self.sslinfo = sslinfo

    def __repr__(self):
        return "Response(%s - %s)"%(self.status_code, self.msg)


class Pathoc(tcp.TCPClient):
    def __init__(
            self,
            address,

            # SSL
            ssl=None,
            sni=None,
            sslversion=4,
            clientcert=None,
            ciphers=None,

            # Output control
            showreq = False,
            showresp = False,
            explain = False,
            hexdump = False,
            ignorecodes = (),
            ignoretimeout = False,
            showsummary = False,
            fp = sys.stderr
    ):
        """
            spec: A request specification
            showreq: Print requests
            showresp: Print responses
            explain: Print request explanation
            showssl: Print info on SSL connection
            hexdump: When printing requests or responses, use hex dump output
            showsummary: Show a summary of requests
            ignorecodes: Sequence of return codes to ignore
        """
        tcp.TCPClient.__init__(self, address)
        self.settings = dict(
            staticdir = os.getcwd(),
            unconstrained_file_access = True,
        )
        self.ssl, self.sni = ssl, sni
        self.clientcert = clientcert
        self.sslversion = utils.SSLVERSIONS[sslversion]
        self.ciphers = ciphers
        self.sslinfo = None

        self.showreq = showreq
        self.showresp = showresp
        self.explain = explain
        self.hexdump = hexdump
        self.ignorecodes = ignorecodes
        self.ignoretimeout = ignoretimeout
        self.showsummary = showsummary
        self.fp = fp

    def http_connect(self, connect_to):
        self.wfile.write(
            'CONNECT %s:%s HTTP/1.1\r\n'%tuple(connect_to) +
            '\r\n'
        )
        self.wfile.flush()
        l = self.rfile.readline()
        if not l:
            raise PathocError("Proxy CONNECT failed")
        parsed = http.parse_response_line(l)
        if not parsed[1] == 200:
            raise PathocError(
                "Proxy CONNECT failed: %s - %s"%(parsed[1], parsed[2])
            )
        http.read_headers(self.rfile)

    def connect(self, connect_to=None, showssl=False, fp=sys.stdout):
        """
            connect_to: A (host, port) tuple, which will be connected to with
            an HTTP CONNECT request.
        """
        tcp.TCPClient.connect(self)
        if connect_to:
            self.http_connect(connect_to)
        self.sslinfo = None
        if self.ssl:
            try:
                self.convert_to_ssl(
                    sni=self.sni,
                    cert=self.clientcert,
                    method=self.sslversion,
                    cipher_list = self.ciphers
                )
            except tcp.NetLibError, v:
                raise PathocError(str(v))
            self.sslinfo = SSLInfo(
                self.connection.get_peer_cert_chain(),
                self.get_current_cipher()
            )
            if showssl:
                print >> fp, str(self.sslinfo)

    def _show_summary(self, fp, resp):
        print >> fp, "<< %s %s: %s bytes"%(
            resp.status_code, utils.xrepr(resp.msg), len(resp.content)
        )

    def _show(self, fp, header, data, hexdump):
        if hexdump:
            print >> fp, "%s (hex dump):"%header
            for line in netlib.utils.hexdump(data):
                print >> fp, "\t%s %s %s"%line
        else:
            print >> fp, "%s (unprintables escaped):"%header
            print >> fp, netlib.utils.cleanBin(data)

    def request(self, r):
        """
            Performs a single request.

            r: A language.Request object, or a string representing one request.

            Returns True if we have a non-ignored response.

            May raise http.HTTPError, tcp.NetLibError
        """
        if isinstance(r, basestring):
            r = language.parse_requests(r)[0]
        resp, req = None, None
        if self.showreq:
            self.wfile.start_log()
        if self.showresp:
            self.rfile.start_log()
        try:
            req = language.serve(
                r,
                self.wfile,
                self.settings,
                requets_host = self.address.host
            )
            self.wfile.flush()
            resp = list(
                http.read_response(self.rfile, r.method.string(), None)
            )
            resp.append(self.sslinfo)
            resp = Response(*resp)
        except http.HttpError, v:
            if self.showsummary:
                print >> self.fp, "<< HTTP Error:", v.message
            raise
        except tcp.NetLibTimeout:
            if self.ignoretimeout:
                return None
            if self.showsummary:
                print >> self.fp, "<<", "Timeout"
            raise
        except tcp.NetLibDisconnect: # pragma: nocover
            if self.showsummary:
                print >> self.fp, "<<", "Disconnect"
            raise
        finally:
            if req:
                if resp and resp.status_code in self.ignorecodes:
                    resp = None
                else:
                    if self.explain:
                        print >> self.fp, ">> Spec:", r.spec()

                    if self.showreq:
                        self._show(
                            self.fp, ">> Request",
                            self.wfile.get_log(),
                            self.hexdump
                        )

                    if self.showsummary and resp:
                        self._show_summary(self.fp, resp)
                    if self.showresp:
                        self._show(
                            self.fp,
                            "<< Response",
                            self.rfile.get_log(),
                            self.hexdump
                        )
        return resp


def main(args): # pragma: nocover
    memo = set([])
    trycount = 0
    try:
        cnt = 0
        while 1:
            if cnt == args.repeat and args.repeat != 0:
                break
            if trycount > args.memolimit:
                print >> sys.stderr, "Memo limit exceeded..."
                return
            if args.wait and cnt != 0:
                time.sleep(args.wait)

            cnt += 1
            if args.random:
                playlist = [random.choice(args.requests)]
            else:
                playlist = args.requests
            p = Pathoc(
                (args.host, args.port),
                ssl = args.ssl,
                sni = args.sni,
                sslversion = args.sslversion,
                clientcert = args.clientcert,
                ciphers = args.ciphers,
                showreq = args.showreq,
                showresp = args.showresp,
                explain = args.explain,
                hexdump = args.hexdump,
                ignorecodes = args.ignorecodes,
                ignoretimeout = args.ignoretimeout,
                showsummary = True
            )
            if args.explain or args.memo:
                playlist = [
                    i.freeze(p.settings, p.address.host) for i in playlist
                ]
            if args.memo:
                newlist = []
                for spec in playlist:
                    h = hashlib.sha256(spec.spec()).digest()
                    if h not in memo:
                        memo.add(h)
                        newlist.append(spec)
                playlist = newlist
            if not playlist:
                trycount += 1
                continue

            trycount = 0
            try:
                p.connect(args.connect_to, args.showssl)
            except tcp.NetLibError, v:
                print >> sys.stderr, str(v)
                continue
            except PathocError, v:
                print >> sys.stderr, str(v)
                sys.exit(1)
            if args.timeout:
                p.settimeout(args.timeout)
            for spec in playlist:
                try:
                    ret = p.request(spec)
                    sys.stdout.flush()
                    if ret and args.oneshot:
                        return
                except (http.HttpError, tcp.NetLibError), v:
                    pass
    except KeyboardInterrupt:
        pass
