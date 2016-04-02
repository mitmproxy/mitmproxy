import contextlib
import sys
import os
import itertools
import hashlib
from six.moves import queue
import random
import select
import time
import threading

import OpenSSL.crypto
import six

from netlib import tcp, http, certutils, websockets, socks
from netlib.exceptions import HttpException, TcpDisconnect, TcpTimeout, TlsException, TcpException, \
    NetlibException
from netlib.http import http1, http2

import language.http
import language.websockets
from . import utils, log

import logging
from netlib.tutils import treq

logging.getLogger("hpack").setLevel(logging.WARNING)


class PathocError(Exception):
    pass


class SSLInfo(object):

    def __init__(self, certchain, cipher, alp):
        self.certchain, self.cipher, self.alp = certchain, cipher, alp

    def __str__(self):
        parts = [
            "Application Layer Protocol: %s" % self.alp,
            "Cipher: %s, %s bit, %s" % self.cipher,
            "SSL certificate chain:"
        ]
        for n,i in enumerate(self.certchain):
            parts.append("  Certificate [%s]" % n)
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



class WebsocketFrameReader(threading.Thread):

    def __init__(
            self,
            rfile,
            logfp,
            showresp,
            hexdump,
            ws_read_limit,
            timeout
    ):
        threading.Thread.__init__(self)
        self.timeout = timeout
        self.ws_read_limit = ws_read_limit
        self.logfp = logfp
        self.showresp = showresp
        self.hexdump = hexdump
        self.rfile = rfile
        self.terminate = queue.Queue()
        self.frames_queue = queue.Queue()
        self.logger = log.ConnectionLogger(
            self.logfp,
            self.hexdump,
            rfile if showresp else None,
            None
        )

    @contextlib.contextmanager
    def terminator(self):
        yield
        self.frames_queue.put(None)

    def run(self):
        starttime = time.time()
        with self.terminator():
            while True:
                if self.ws_read_limit == 0:
                    return
                r, _, _ = select.select([self.rfile], [], [], 0.05)
                delta = time.time() - starttime
                if not r and self.timeout and delta > self.timeout:
                    return
                try:
                    self.terminate.get_nowait()
                    return
                except queue.Empty:
                    pass
                for rfile in r:
                    with self.logger.ctx() as log:
                        try:
                            frm = websockets.Frame.from_file(self.rfile)
                        except TcpDisconnect:
                            return
                        self.frames_queue.put(frm)
                        log("<< %s" % frm.header.human_readable())
                        if self.ws_read_limit is not None:
                            self.ws_read_limit -= 1
                        starttime = time.time()


class Pathoc(tcp.TCPClient):

    def __init__(
            self,
            address,

            # SSL
            ssl=None,
            sni=None,
            ssl_version=tcp.SSL_DEFAULT_METHOD,
            ssl_options=tcp.SSL_DEFAULT_OPTIONS,
            clientcert=None,
            ciphers=None,

            # HTTP/2
            use_http2=False,
            http2_skip_connection_preface=False,
            http2_framedump=False,

            # Websockets
            ws_read_limit=None,

            # Network
            timeout=None,

            # Output control
            showreq=False,
            showresp=False,
            explain=False,
            hexdump=False,
            ignorecodes=(),
            ignoretimeout=False,
            showsummary=False,
            fp=sys.stdout
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

        self.ssl, self.sni = ssl, sni
        self.clientcert = clientcert
        self.ssl_version = ssl_version
        self.ssl_options = ssl_options
        self.ciphers = ciphers
        self.sslinfo = None

        self.use_http2 = use_http2
        self.http2_skip_connection_preface = http2_skip_connection_preface
        self.http2_framedump = http2_framedump

        self.ws_read_limit = ws_read_limit

        self.timeout = timeout

        self.showreq = showreq
        self.showresp = showresp
        self.explain = explain
        self.hexdump = hexdump
        self.ignorecodes = ignorecodes
        self.ignoretimeout = ignoretimeout
        self.showsummary = showsummary
        self.fp = fp

        self.ws_framereader = None

        if self.use_http2:
            if not tcp.HAS_ALPN:  # pragma: no cover
                log.write_raw(
                    self.fp,
                    "HTTP/2 requires ALPN support. "
                    "Please use OpenSSL >= 1.0.2. "
                    "Pathoc might not be working as expected without ALPN."
                )
            self.protocol = http2.HTTP2Protocol(self, dump_frames=self.http2_framedump)
        else:
            self.protocol = http1

        self.settings = language.Settings(
            is_client=True,
            staticdir=os.getcwd(),
            unconstrained_file_access=True,
            request_host=self.address.host,
            protocol=self.protocol,
        )

    def http_connect(self, connect_to):
        self.wfile.write(
            'CONNECT %s:%s HTTP/1.1\r\n' % tuple(connect_to) +
            '\r\n'
        )
        self.wfile.flush()
        try:
            resp = self.protocol.read_response(self.rfile, treq(method="CONNECT"))
            if resp.status_code != 200:
                raise HttpException("Unexpected status code: %s" % resp.status_code)
        except HttpException as e:
            six.reraise(PathocError, PathocError(
                "Proxy CONNECT failed: %s" % repr(e)
            ))

    def socks_connect(self, connect_to):
        try:
            client_greet = socks.ClientGreeting(socks.VERSION.SOCKS5, [socks.METHOD.NO_AUTHENTICATION_REQUIRED])
            client_greet.to_file(self.wfile)
            self.wfile.flush()

            server_greet = socks.ServerGreeting.from_file(self.rfile)
            server_greet.assert_socks5()
            if server_greet.method != socks.METHOD.NO_AUTHENTICATION_REQUIRED:
                raise socks.SocksError(
                    socks.METHOD.NO_ACCEPTABLE_METHODS,
                    "pathoc only supports SOCKS without authentication"
                )

            connect_request = socks.Message(
                socks.VERSION.SOCKS5,
                socks.CMD.CONNECT,
                socks.ATYP.DOMAINNAME,
                tcp.Address.wrap(connect_to)
            )
            connect_request.to_file(self.wfile)
            self.wfile.flush()

            connect_reply = socks.Message.from_file(self.rfile)
            connect_reply.assert_socks5()
            if connect_reply.msg != socks.REP.SUCCEEDED:
                raise socks.SocksError(
                    connect_reply.msg,
                    "SOCKS server error"
                )
        except (socks.SocksError, TcpDisconnect) as e:
            raise PathocError(str(e))

    def connect(self, connect_to=None, showssl=False, fp=sys.stdout):
        """
            connect_to: A (host, port) tuple, which will be connected to with
            an HTTP CONNECT request.
        """
        if self.use_http2 and not self.ssl:
            raise NotImplementedError("HTTP2 without SSL is not supported.")

        tcp.TCPClient.connect(self)

        if connect_to:
            self.http_connect(connect_to)

        self.sslinfo = None
        if self.ssl:
            try:
                alpn_protos = [b'http/1.1']
                if self.use_http2:
                    alpn_protos.append(b'h2')

                self.convert_to_ssl(
                    sni=self.sni,
                    cert=self.clientcert,
                    method=self.ssl_version,
                    options=self.ssl_options,
                    cipher_list=self.ciphers,
                    alpn_protos=alpn_protos
                )
            except TlsException as v:
                raise PathocError(str(v))

            self.sslinfo = SSLInfo(
                self.connection.get_peer_cert_chain(),
                self.get_current_cipher(),
                self.get_alpn_proto_negotiated()
            )
            if showssl:
                print >> fp, str(self.sslinfo)

            if self.use_http2:
                self.protocol.check_alpn()
                if not self.http2_skip_connection_preface:
                    self.protocol.perform_client_connection_preface()

        if self.timeout:
            self.settimeout(self.timeout)

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
                        timeout=timeout,
                        block=True if timeout != 0 else False
                    )
                except queue.Empty:
                    if finish:
                        continue
                    else:
                        return
                if frm is None:
                    self.ws_framereader.join()
                    return
                yield frm

    def websocket_send_frame(self, r):
        """
            Sends a single websocket frame.
        """
        logger = log.ConnectionLogger(
            self.fp,
            self.hexdump,
            None,
            self.wfile if self.showreq else None,
        )
        with logger.ctx() as lg:
            lg(">> %s" % r)
            language.serve(r, self.wfile, self.settings)
            self.wfile.flush()

    def websocket_start(self, r):
        """
            Performs an HTTP request, and attempts to drop into websocket
            connection.
        """
        resp = self.http(r)
        if resp.status_code == 101:
            self.ws_framereader = WebsocketFrameReader(
                self.rfile,
                self.fp,
                self.showresp,
                self.hexdump,
                self.ws_read_limit,
                self.timeout
            )
            self.ws_framereader.start()
        return resp

    def http(self, r):
        """
            Performs a single request.

            r: A language.http.Request object, or a string representing one
            request.

            Returns Response if we have a non-ignored response.

            May raise a NetlibException
        """
        logger = log.ConnectionLogger(
            self.fp,
            self.hexdump,
            self.rfile if self.showresp else None,
            self.wfile if self.showreq else None,
        )
        with logger.ctx() as lg:
            lg(">> %s" % r)
            resp, req = None, None
            try:
                req = language.serve(r, self.wfile, self.settings)
                self.wfile.flush()

                resp = self.protocol.read_response(self.rfile, treq(method=req["method"].encode()))
                resp.sslinfo = self.sslinfo
            except HttpException as v:
                lg("Invalid server response: %s" % v)
                raise
            except TcpTimeout:
                if self.ignoretimeout:
                    lg("Timeout (ignored)")
                    return None
                lg("Timeout")
                raise
            finally:
                if resp:
                    lg("<< %s %s: %s bytes" % (
                        resp.status_code, utils.xrepr(resp.reason), len(resp.content)
                    ))
                    if resp.status_code in self.ignorecodes:
                        lg.suppress()
            return resp

    def request(self, r):
        """
            Performs a single request.

            r: A language.message.Messsage object, or a string representing
            one.

            Returns Response if we have a non-ignored response.

            May raise a NetlibException
        """
        if isinstance(r, basestring):
            r = language.parse_pathoc(r, self.use_http2).next()

        if isinstance(r, language.http.Request):
            if r.ws:
                return self.websocket_start(r)
            else:
                return self.http(r)
        elif isinstance(r, language.websockets.WebsocketFrame):
            self.websocket_send_frame(r)
        elif isinstance(r, language.http2.Request):
            return self.http(r)
        # elif isinstance(r, language.http2.Frame):
            # TODO: do something


def main(args):  # pragma: no cover
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
                ssl=args.ssl,
                sni=args.sni,
                ssl_version=args.ssl_version,
                ssl_options=args.ssl_options,
                clientcert=args.clientcert,
                ciphers=args.ciphers,
                use_http2=args.use_http2,
                http2_skip_connection_preface=args.http2_skip_connection_preface,
                http2_framedump=args.http2_framedump,
                showreq=args.showreq,
                showresp=args.showresp,
                explain=args.explain,
                hexdump=args.hexdump,
                ignorecodes=args.ignorecodes,
                timeout=args.timeout,
                ignoretimeout=args.ignoretimeout,
                showsummary=True
            )
            trycount = 0
            try:
                p.connect(args.connect_to, args.showssl)
            except TcpException as v:
                print >> sys.stderr, str(v)
                continue
            except PathocError as v:
                print >> sys.stderr, str(v)
                sys.exit(1)
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
                    for i_ in p.wait(timeout=0, finish=False):
                        pass
                except NetlibException:
                    break
            for i_ in p.wait(timeout=0.01, finish=True):
                pass
    except KeyboardInterrupt:
        pass
    if p:
        p.stop()
