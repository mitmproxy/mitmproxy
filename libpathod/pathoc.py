import sys
import os
import itertools
import hashlib
import Queue
import random
import select
import time
import threading

import OpenSSL.crypto

from netlib import tcp, http, certutils, websockets

import language.http
import language.websockets
from . import utils, log


class PathocError(Exception):
    pass


class SSLInfo:
    def __init__(self, certchain, cipher):
        self.certchain, self.cipher = certchain, cipher

    def __str__(self):
        parts = [
            "Cipher: %s, %s bit, %s" % self.cipher,
            "SSL certificate chain:"
        ]
        for i in self.certchain:
            parts.append("\tSubject: ")
            for cn in i.get_subject().get_components():
                parts.append("\t\t%s=%s" % cn)
            parts.append("\tIssuer: ")
            for cn in i.get_issuer().get_components():
                parts.append("\t\t%s=%s" % cn)
            parts.extend(
                [
                    "\tVersion: %s" % i.get_version(),
                    "\tValidity: %s - %s" % (
                        i.get_notBefore(), i.get_notAfter()
                    ),
                    "\tSerial: %s" % i.get_serial_number(),
                    "\tAlgorithm: %s" % i.get_signature_algorithm()
                ]
            )
            pk = i.get_pubkey()
            types = {
                OpenSSL.crypto.TYPE_RSA: "RSA",
                OpenSSL.crypto.TYPE_DSA: "DSA"
            }
            t = types.get(pk.type(), "Uknown")
            parts.append("\tPubkey: %s bit %s" % (pk.bits(), t))
            s = certutils.SSLCert(i)
            if s.altnames:
                parts.append("\tSANs: %s" % " ".join(s.altnames))
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
        return "Response(%s - %s)" % (self.status_code, self.msg)


class WebsocketFrameReader(threading.Thread):
    def __init__(
            self,
            rfile,
            logfp,
            showresp,
            hexdump,
            ws_read_limit):
        threading.Thread.__init__(self)
        self.ws_read_limit = ws_read_limit
        self.logfp = logfp
        self.showresp = showresp
        self.hexdump = hexdump
        self.rfile = rfile
        self.terminate = Queue.Queue()
        self.frames_queue = Queue.Queue()

    def log(self, rfile):
        return log.Log(
            self.logfp,
            self.hexdump,
            rfile if self.showresp else None,
            None
        )

    def run(self):
        while True:
            if self.ws_read_limit == 0:
                break
            r, _, _ = select.select([self.rfile], [], [], 0.05)
            try:
                self.terminate.get_nowait()
                break
            except Queue.Empty:
                pass
            for rfile in r:
                with self.log(rfile) as log:
                    try:
                        frm = websockets.Frame.from_file(self.rfile)
                    except tcp.NetLibError:
                        self.ws_read_limit = 0
                        break
                    self.frames_queue.put(frm)
                    log("<< %s" % frm.header.human_readable())
                    if self.ws_read_limit is not None:
                        self.ws_read_limit -= 1
        self.frames_queue.put(None)


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

            # Websockets
            ws_read_limit = None,

            # Output control
            showreq = False,
            showresp = False,
            explain = False,
            hexdump = False,
            ignorecodes = (),
            ignoretimeout = False,
            showsummary = False,
            fp = sys.stdout
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
        self.settings = language.Settings(
            staticdir = os.getcwd(),
            unconstrained_file_access = True,
            request_host = self.address.host,
            is_client = True
        )
        self.ssl, self.sni = ssl, sni
        self.clientcert = clientcert
        self.sslversion = utils.SSLVERSIONS[sslversion]
        self.ciphers = ciphers
        self.sslinfo = None

        self.ws_read_limit = ws_read_limit

        self.showreq = showreq
        self.showresp = showresp
        self.explain = explain
        self.hexdump = hexdump
        self.ignorecodes = ignorecodes
        self.ignoretimeout = ignoretimeout
        self.showsummary = showsummary
        self.fp = fp

        self.ws_framereader = None

    def log(self):
        return log.Log(
            self.fp,
            self.hexdump,
            self.rfile if self.showresp else None,
            self.wfile if self.showreq else None,
        )

    def http_connect(self, connect_to):
        self.wfile.write(
            'CONNECT %s:%s HTTP/1.1\r\n' % tuple(connect_to) +
            '\r\n'
        )
        self.wfile.flush()
        l = self.rfile.readline()
        if not l:
            raise PathocError("Proxy CONNECT failed")
        parsed = http.parse_response_line(l)
        if not parsed[1] == 200:
            raise PathocError(
                "Proxy CONNECT failed: %s - %s" % (parsed[1], parsed[2])
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
            except tcp.NetLibError as v:
                raise PathocError(str(v))
            self.sslinfo = SSLInfo(
                self.connection.get_peer_cert_chain(),
                self.get_current_cipher()
            )
            if showssl:
                print >> fp, str(self.sslinfo)

    def _resp_summary(self, resp):
        return "<< %s %s: %s bytes" % (
            resp.status_code, utils.xrepr(resp.msg), len(resp.content)
        )

    def stop(self):
        if self.ws_framereader:
            self.ws_framereader.terminate.put(None)

    def wait(self, timeout=0.01, finish=True):
        """
            A generator that yields frames until Pathoc terminates.

            timeout: If specified None may be yielded instead if timeout is
            reached. If timeout is None, wait forever. If timeout is 0, return
            immedately if nothing is on the queue.

            finish: If true, consume messages until the reader shuts down.
            Otherwise, return None on timeout.
        """
        if self.ws_framereader:
            while True:
                try:
                    frm = self.ws_framereader.frames_queue.get(
                        timeout = timeout,
                        block = True if timeout != 0 else False
                    )
                except Queue.Empty:
                    if finish:
                        continue
                    else:
                        return
                if frm is None:
                    self.ws_framereader.join()
                    return
                yield frm

    def websocket_get_frame(self, frame):
        """
            Called when a frame is received from the server.
        """
        pass

    def websocket_send_frame(self, r):
        """
            Sends a single websocket frame.
        """
        with self.log() as log:
            if isinstance(r, basestring):
                r = language.parse_pathoc(r).next()
            log(">> %s" % r)
            try:
                language.serve(r, self.wfile, self.settings)
                self.wfile.flush()
            except tcp.NetLibTimeout:
                if self.ignoretimeout:
                    self.log("Timeout (ignored)")
                    return None
                raise

    def websocket_start(self, r, limit=None):
        """
            Performs an HTTP request, and attempts to drop into websocket
            connection.

            limit: Disconnect after receiving N server frames.
        """
        resp = self.http(r)
        if resp.status_code == 101:
            self.ws_framereader = WebsocketFrameReader(
                self.rfile,
                self.fp,
                self.showresp,
                self.hexdump,
                self.ws_read_limit
            )
            self.ws_framereader.start()
        return resp

    def http(self, r):
        """
            Performs a single request.

            r: A language.http.Request object, or a string representing one
            request.

            Returns Response if we have a non-ignored response.

            May raise http.HTTPError, tcp.NetLibError
        """
        with self.log() as log:
            if isinstance(r, basestring):
                r = language.parse_pathoc(r).next()
            log(">> %s" % r)
            resp, req = None, None
            try:
                req = language.serve(r, self.wfile, self.settings)
                self.wfile.flush()
                resp = list(
                    http.read_response(
                        self.rfile,
                        req["method"],
                        None
                    )
                )
                resp.append(self.sslinfo)
                resp = Response(*resp)
            except http.HttpError, v:
                log("Invalid server response: %s" % v)
                raise
            except tcp.NetLibTimeout:
                if self.ignoretimeout:
                    log("Timeout (ignored)")
                    return None
                log("Timeout")
                raise
            finally:
                if resp:
                    log(self._resp_summary(resp))
                    if resp.status_code in self.ignorecodes:
                        log.suppress()
            return resp

    def request(self, r):
        """
            Performs a single request.

            r: A language.message.Messsage object, or a string representing
            one.

            Returns Response if we have a non-ignored response.

            May raise http.HTTPError, tcp.NetLibError
        """
        if isinstance(r, basestring):
            r = language.parse_pathoc(r).next()
        if isinstance(r, language.http.Request):
            if r.ws:
                return self.websocket_start(r, self.websocket_get_frame)
            else:
                return self.http(r)
        elif isinstance(r, language.websockets.WebsocketFrame):
            self.websocket_send_frame(r)


def main(args):  # pragma: nocover
    memo = set([])
    trycount = 0
    p = None
    try:
        cnt = 0
        while True:
            if cnt == args.repeat and args.repeat != 0:
                break
            if args.wait and cnt != 0:
                time.sleep(args.wait)

            cnt += 1
            playlist = itertools.chain(*args.requests)
            if args.random:
                playlist = random.choice(args.requests)
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
            trycount = 0
            try:
                p.connect(args.connect_to, args.showssl)
            except tcp.NetLibError as v:
                print >> sys.stderr, str(v)
                continue
            except PathocError as v:
                print >> sys.stderr, str(v)
                sys.exit(1)
            if args.timeout:
                p.settimeout(args.timeout)
            for spec in playlist:
                if args.explain or args.memo:
                    spec = spec.freeze(p.settings)
                if args.memo:
                    h = hashlib.sha256(spec.spec()).digest()
                    if h not in memo:
                        trycount = 0
                        memo.add(h)
                    else:
                        trycount += 1
                        if trycount > args.memolimit:
                            print >> sys.stderr, "Memo limit exceeded..."
                            return
                        else:
                            continue
                try:
                    ret = p.request(spec)
                    if ret and args.oneshot:
                        return
                    # We consume the queue when we can, so it doesn't build up.
                    for i in p.wait(timeout=0, finish=False):
                        pass
                except (http.HttpError, tcp.NetLibError) as v:
                    break
            for i in p.wait(timeout=0.01, finish=True):
                pass
    except KeyboardInterrupt:
        pass
    if p:
        p.stop()
