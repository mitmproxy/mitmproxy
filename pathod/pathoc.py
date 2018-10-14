import contextlib
import sys
import os
import itertools
import hashlib
import queue
import random
import select
import time

import OpenSSL.crypto
import logging

from mitmproxy import certs
from mitmproxy import exceptions
from mitmproxy.net import tcp, tls
from mitmproxy.net import websockets
from mitmproxy.net import socks
from mitmproxy.net import http as net_http
from mitmproxy.coretypes import basethread
from mitmproxy.utils import strutils

from pathod import log
from pathod import language
from pathod.protocols import http2


logging.getLogger("hpack").setLevel(logging.WARNING)


def xrepr(s):
    return repr(s)[1:-1]


class PathocError(Exception):
    pass


class SSLInfo:

    def __init__(self, certchain, cipher, alp):
        self.certchain, self.cipher, self.alp = certchain, cipher, alp

    def __str__(self):
        parts = [
            "Application Layer Protocol: %s" % strutils.always_str(self.alp, "utf8"),
            "Cipher: %s, %s bit, %s" % self.cipher,
            "SSL certificate chain:"
        ]
        for n, i in enumerate(self.certchain):
            parts.append("  Certificate [%s]" % n)
            parts.append("\tSubject: ")
            for cn in i.get_subject().get_components():
                parts.append("\t\t%s=%s" % (
                    strutils.always_str(cn[0], "utf8"),
                    strutils.always_str(cn[1], "utf8"))
                )
            parts.append("\tIssuer: ")
            for cn in i.get_issuer().get_components():
                parts.append("\t\t%s=%s" % (
                    strutils.always_str(cn[0], "utf8"),
                    strutils.always_str(cn[1], "utf8"))
                )
            parts.extend(
                [
                    "\tVersion: %s" % i.get_version(),
                    "\tValidity: %s - %s" % (
                        strutils.always_str(i.get_notBefore(), "utf8"),
                        strutils.always_str(i.get_notAfter(), "utf8")
                    ),
                    "\tSerial: %s" % i.get_serial_number(),
                    "\tAlgorithm: %s" % strutils.always_str(i.get_signature_algorithm(), "utf8")
                ]
            )
            pk = i.get_pubkey()
            types = {
                OpenSSL.crypto.TYPE_RSA: "RSA",
                OpenSSL.crypto.TYPE_DSA: "DSA"
            }
            t = types.get(pk.type(), "Uknown")
            parts.append("\tPubkey: %s bit %s" % (pk.bits(), t))
            s = certs.Cert(i)
            if s.altnames:
                parts.append("\tSANs: %s" % " ".join(strutils.always_str(n, "utf8") for n in s.altnames))
        return "\n".join(parts)


class WebsocketFrameReader(basethread.BaseThread):

    def __init__(
            self,
            rfile,
            logfp,
            showresp,
            hexdump,
            ws_read_limit,
            timeout
    ):
        basethread.BaseThread.__init__(self, "WebsocketFrameReader")
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
            False,
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
                try:
                    r, _, _ = select.select([self.rfile], [], [], 0.05)
                except OSError:  # pragma: no cover
                    return  # this is not reliably triggered due to its nature, so we exclude it from coverage.
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
                        except exceptions.TcpDisconnect:
                            return
                        self.frames_queue.put(frm)
                        log("<< %s" % repr(frm.header))
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
            ssl_version=tls.DEFAULT_METHOD,
            ssl_options=tls.DEFAULT_OPTIONS,
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
            self.protocol = http2.HTTP2StateProtocol(self, dump_frames=self.http2_framedump)
        else:
            self.protocol = net_http.http1

        self.settings = language.Settings(
            is_client=True,
            staticdir=os.getcwd(),
            unconstrained_file_access=True,
            request_host=self.address[0],
            protocol=self.protocol,
        )

    def http_connect(self, connect_to):
        req = net_http.Request(
            first_line_format='authority',
            method='CONNECT',
            scheme=None,
            host=connect_to[0].encode("idna"),
            port=connect_to[1],
            path=None,
            http_version='HTTP/1.1',
            headers=[(b"Host", connect_to[0].encode("idna"))],
            content=b'',
        )
        self.wfile.write(net_http.http1.assemble_request(req))
        self.wfile.flush()
        try:
            resp = self.protocol.read_response(self.rfile, req)
            if resp.status_code != 200:
                raise exceptions.HttpException("Unexpected status code: %s" % resp.status_code)
        except exceptions.HttpException as e:
            raise PathocError(
                "Proxy CONNECT failed: %s" % repr(e)
            )

    def socks_connect(self, connect_to):
        try:
            client_greet = socks.ClientGreeting(
                socks.VERSION.SOCKS5,
                [socks.METHOD.NO_AUTHENTICATION_REQUIRED]
            )
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
                connect_to,
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
        except (socks.SocksError, exceptions.TcpDisconnect) as e:
            raise PathocError(str(e))

    def connect(self, connect_to=None, showssl=False, fp=sys.stdout):
        """
            connect_to: A (host, port) tuple, which will be connected to with
            an HTTP CONNECT request.
        """
        if self.use_http2 and not self.ssl:
            raise NotImplementedError("HTTP2 without SSL is not supported.")

        with tcp.TCPClient.connect(self) as closer:
            if connect_to:
                self.http_connect(connect_to)

            self.sslinfo = None
            if self.ssl:
                try:
                    alpn_protos = [b'http/1.1']
                    if self.use_http2:
                        alpn_protos.append(b'h2')

                    self.convert_to_tls(
                        sni=self.sni,
                        cert=self.clientcert,
                        method=self.ssl_version,
                        options=self.ssl_options,
                        cipher_list=self.ciphers,
                        alpn_protos=alpn_protos
                    )
                except exceptions.TlsException as v:
                    raise PathocError(str(v))

                self.sslinfo = SSLInfo(
                    self.connection.get_peer_cert_chain(),
                    self.get_current_cipher(),
                    self.get_alpn_proto_negotiated()
                )
                if showssl:
                    print(str(self.sslinfo), file=fp)

                if self.use_http2:
                    self.protocol.check_alpn()
                    if not self.http2_skip_connection_preface:
                        self.protocol.perform_client_connection_preface()

            if self.timeout:
                self.settimeout(self.timeout)

            return closer.pop()

    def stop(self):
        if self.ws_framereader:
            self.ws_framereader.terminate.put(None)

    def wait(self, timeout=0.01, finish=True):
        """
            A generator that yields frames until Pathoc terminates.

            timeout: If specified None may be yielded instead if timeout is
            reached. If timeout is None, wait forever. If timeout is 0, return
            immediately if nothing is on the queue.

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
                    self.ws_framereader = None
                    return
                yield frm

    def websocket_send_frame(self, r):
        """
            Sends a single websocket frame.
        """
        logger = log.ConnectionLogger(
            self.fp,
            self.hexdump,
            False,
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

            May raise a exceptions.NetlibException
        """
        logger = log.ConnectionLogger(
            self.fp,
            self.hexdump,
            False,
            self.rfile if self.showresp else None,
            self.wfile if self.showreq else None,
        )
        with logger.ctx() as lg:
            lg(">> %s" % r)
            resp, req = None, None
            try:
                req = language.serve(r, self.wfile, self.settings)
                self.wfile.flush()

                # build a dummy request to read the response
                # ideally this would be returned directly from language.serve
                dummy_req = net_http.Request(
                    first_line_format="relative",
                    method=req["method"],
                    scheme=b"http",
                    host=b"localhost",
                    port=80,
                    path=b"/",
                    http_version=b"HTTP/1.1",
                    content=b'',
                )

                resp = self.protocol.read_response(self.rfile, dummy_req)
                resp.sslinfo = self.sslinfo
            except exceptions.HttpException as v:
                lg("Invalid server response: %s" % v)
                raise
            except exceptions.TcpTimeout:
                if self.ignoretimeout:
                    lg("Timeout (ignored)")
                    return None
                lg("Timeout")
                raise
            finally:
                if resp:
                    lg("<< %s %s: %s bytes" % (
                        resp.status_code, strutils.escape_control_characters(resp.reason) if resp.reason else "", len(resp.content)
                    ))
                    if resp.status_code in self.ignorecodes:
                        lg.suppress()
            return resp

    def request(self, r):
        """
            Performs a single request.

            r: A language.message.Message object, or a string representing
            one.

            Returns Response if we have a non-ignored response.

            May raise a exceptions.NetlibException
        """
        if isinstance(r, str):
            r = next(language.parse_pathoc(r, self.use_http2))

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
    memo = set()
    p = None

    if args.repeat == 1:
        requests = args.requests
    else:
        # If we are replaying more than once, we must convert the request generators to lists
        # or they will be exhausted after the first run.
        # This is bad for the edge-case where get:/:x10000000 (see 0da3e51) is combined with -n 2,
        # but does not matter otherwise.
        requests = [list(x) for x in args.requests]

    try:
        requests_done = 0
        while True:
            if requests_done == args.repeat:
                break
            if args.wait and requests_done > 0:
                time.sleep(args.wait)

            requests_done += 1
            if args.random:
                playlist = random.choice(requests)
            else:
                playlist = itertools.chain.from_iterable(requests)
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
                with p.connect(args.connect_to, args.showssl):
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
                                    print("Memo limit exceeded...", file=sys.stderr)
                                    return
                                else:
                                    continue
                        try:
                            ret = p.request(spec)
                            if ret and args.oneshot:
                                return
                            # We consume the queue when we can, so it doesn't build up.
                            for _ in p.wait(timeout=0, finish=False):
                                pass
                        except exceptions.NetlibException:
                            break
                    for _ in p.wait(timeout=0.01, finish=True):
                        pass
            except exceptions.TcpException as v:
                print(str(v), file=sys.stderr)
                continue
            except PathocError as v:
                print(str(v), file=sys.stderr)
                sys.exit(1)

    except KeyboardInterrupt:
        pass
    if p:
        p.stop()
