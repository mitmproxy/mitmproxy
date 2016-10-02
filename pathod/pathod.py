from __future__ import print_function
import copy
import logging
import os
import sys
import threading

from netlib import tcp
from netlib import certutils
from netlib import websockets
from netlib import version

from six.moves import urllib
from netlib.exceptions import HttpException, HttpReadDisconnect, TcpTimeout, TcpDisconnect, \
    TlsException

from . import language, utils, log, protocols


DEFAULT_CERT_DOMAIN = b"pathod.net"
CONFDIR = "~/.mitmproxy"
CERTSTORE_BASENAME = "mitmproxy"
CA_CERT_NAME = "mitmproxy-ca.pem"
DEFAULT_CRAFT_ANCHOR = "/p/"

logger = logging.getLogger('pathod')


class PathodError(Exception):
    pass


class SSLOptions(object):
    def __init__(
        self,
        confdir=CONFDIR,
        cn=None,
        sans=(),
        not_after_connect=None,
        request_client_cert=False,
        ssl_version=tcp.SSL_DEFAULT_METHOD,
        ssl_options=tcp.SSL_DEFAULT_OPTIONS,
        ciphers=None,
        certs=None,
        alpn_select=b'h2',
    ):
        self.confdir = confdir
        self.cn = cn
        self.sans = sans
        self.not_after_connect = not_after_connect
        self.request_client_cert = request_client_cert
        self.ssl_version = ssl_version
        self.ssl_options = ssl_options
        self.ciphers = ciphers
        self.alpn_select = alpn_select
        self.certstore = certutils.CertStore.from_store(
            os.path.expanduser(confdir),
            CERTSTORE_BASENAME
        )
        for i in certs or []:
            self.certstore.add_cert_file(*i)

    def get_cert(self, name):
        if self.cn:
            name = self.cn
        elif not name:
            name = DEFAULT_CERT_DOMAIN
        return self.certstore.get_cert(name, self.sans)


class PathodHandler(tcp.BaseHandler):
    wbufsize = 0
    sni = None

    def __init__(
        self,
        connection,
        address,
        server,
        logfp,
        settings,
        http2_framedump=False
    ):
        tcp.BaseHandler.__init__(self, connection, address, server)
        self.logfp = logfp
        self.settings = copy.copy(settings)
        self.protocol = None
        self.use_http2 = False
        self.http2_framedump = http2_framedump

    def handle_sni(self, connection):
        sni = connection.get_servername()
        if sni:
            sni = sni.decode("idna")
        self.sni = sni

    def http_serve_crafted(self, crafted, logctx):
        error, crafted = self.server.check_policy(
            crafted, self.settings
        )
        if error:
            err = self.make_http_error_response(error)
            language.serve(err, self.wfile, self.settings)
            return None, dict(
                type="error",
                msg=error
            )

        if self.server.explain and not hasattr(crafted, 'is_error_response'):
            crafted = crafted.freeze(self.settings)
            logctx(">> Spec: %s" % crafted.spec())

        response_log = language.serve(
            crafted,
            self.wfile,
            self.settings
        )
        if response_log["disconnect"]:
            return None, response_log
        return self.handle_http_request, response_log

    def handle_http_request(self, logger):
        """
            Returns a (handler, log) tuple.

            handler: Handler for the next request, or None to disconnect
            log: A dictionary, or None
        """
        with logger.ctx() as lg:
            try:
                req = self.protocol.read_request(self.rfile)
            except HttpReadDisconnect:
                return None, None
            except HttpException as s:
                s = str(s)
                lg(s)
                return None, dict(type="error", msg=s)

            if req.method == 'CONNECT':
                return self.protocol.handle_http_connect([req.host, req.port, req.http_version], lg)

            method = req.method
            path = req.path
            http_version = req.http_version
            headers = req.headers

            clientcert = None
            if self.clientcert:
                clientcert = dict(
                    cn=self.clientcert.cn,
                    subject=self.clientcert.subject,
                    serial=self.clientcert.serial,
                    notbefore=self.clientcert.notbefore.isoformat(),
                    notafter=self.clientcert.notafter.isoformat(),
                    keyinfo=self.clientcert.keyinfo,
                )

            retlog = dict(
                type="crafted",
                protocol="http",
                request=dict(
                    path=path,
                    method=method,
                    headers=headers.fields,
                    http_version=http_version,
                    sni=self.sni,
                    remote_address=self.address(),
                    clientcert=clientcert,
                ),
                cipher=None,
            )
            if self.ssl_established:
                retlog["cipher"] = self.get_current_cipher()

            m = utils.MemBool()

            valid_websocket_handshake = websockets.check_handshake(headers)
            self.settings.websocket_key = websockets.get_client_key(headers)

            # If this is a websocket initiation, we respond with a proper
            # server response, unless over-ridden.
            if valid_websocket_handshake:
                anchor_gen = language.parse_pathod("ws")
            else:
                anchor_gen = None

            for regex, spec in self.server.anchors:
                if regex.match(path):
                    anchor_gen = language.parse_pathod(spec, self.use_http2)
                    break
            else:
                if m(path.startswith(self.server.craftanchor)):
                    spec = urllib.parse.unquote(path)[len(self.server.craftanchor):]
                    if spec:
                        try:
                            anchor_gen = language.parse_pathod(spec, self.use_http2)
                        except language.ParseException as v:
                            lg("Parse error: %s" % v.msg)
                            anchor_gen = iter([self.make_http_error_response(
                                "Parse Error",
                                "Error parsing response spec: %s\n" % (
                                    v.msg + v.marked()
                                )
                            )])
                else:
                    if self.use_http2:
                        anchor_gen = iter([self.make_http_error_response(
                            "Spec Error",
                            "HTTP/2 only supports request/response with the craft anchor point: %s" %
                            self.server.craftanchor
                        )])

            if not anchor_gen:
                anchor_gen = iter([self.make_http_error_response(
                    "Not found",
                    "No valid craft request found"
                )])

            spec = next(anchor_gen)

            if self.use_http2 and isinstance(spec, language.http2.Response):
                spec.stream_id = req.stream_id

            lg("crafting spec: %s" % spec)
            nexthandler, retlog["response"] = self.http_serve_crafted(
                spec,
                lg
            )
            if nexthandler and valid_websocket_handshake:
                self.protocol = protocols.websockets.WebsocketsProtocol(self)
                return self.protocol.handle_websocket, retlog
            else:
                return nexthandler, retlog

    def make_http_error_response(self, reason, body=None):
        resp = self.protocol.make_error_response(reason, body)
        resp.is_error_response = True
        return resp

    def handle(self):
        self.settimeout(self.server.timeout)

        if self.server.ssl:
            try:
                cert, key, _ = self.server.ssloptions.get_cert(None)
                self.convert_to_ssl(
                    cert,
                    key,
                    handle_sni=self.handle_sni,
                    request_client_cert=self.server.ssloptions.request_client_cert,
                    cipher_list=self.server.ssloptions.ciphers,
                    method=self.server.ssloptions.ssl_version,
                    options=self.server.ssloptions.ssl_options,
                    alpn_select=self.server.ssloptions.alpn_select,
                )
            except TlsException as v:
                s = str(v)
                self.server.add_log(
                    dict(
                        type="error",
                        msg=s
                    )
                )
                log.write_raw(self.logfp, s)
                return

            alp = self.get_alpn_proto_negotiated()
            if alp == b'h2':
                self.protocol = protocols.http2.HTTP2Protocol(self)
                self.use_http2 = True

        if not self.protocol:
            self.protocol = protocols.http.HTTPProtocol(self)

        lr = self.rfile if self.server.logreq else None
        lw = self.wfile if self.server.logresp else None
        logger = log.ConnectionLogger(self.logfp, self.server.hexdump, True, lr, lw)

        self.settings.protocol = self.protocol

        handler = self.handle_http_request

        while not self.finished:
            handler, l = handler(logger)
            if l:
                self.addlog(l)
            if not handler:
                return

    def addlog(self, log):
        if self.server.logreq:
            log["request_bytes"] = self.rfile.get_log()
        if self.server.logresp:
            log["response_bytes"] = self.wfile.get_log()
        self.server.add_log(log)


class Pathod(tcp.TCPServer):
    LOGBUF = 500

    def __init__(
        self,
        addr,
        ssl=False,
        ssloptions=None,
        craftanchor=DEFAULT_CRAFT_ANCHOR,
        staticdir=None,
        anchors=(),
        sizelimit=None,
        nocraft=False,
        nohang=False,
        timeout=None,
        logreq=False,
        logresp=False,
        explain=False,
        hexdump=False,
        http2_framedump=False,
        webdebug=False,
        logfp=sys.stdout,
    ):
        """
            addr: (address, port) tuple. If port is 0, a free port will be
            automatically chosen.
            ssloptions: an SSLOptions object.
            craftanchor: URL prefix specifying the path under which to anchor
            response generation.
            staticdir: path to a directory of static resources, or None.
            anchors: List of (regex object, language.Request object) tuples, or
            None.
            sizelimit: Limit size of served data.
            nocraft: Disable response crafting.
            nohang: Disable pauses.
        """
        tcp.TCPServer.__init__(self, addr)
        self.ssl = ssl
        self.ssloptions = ssloptions or SSLOptions()
        self.staticdir = staticdir
        self.craftanchor = craftanchor
        self.sizelimit = sizelimit
        self.nocraft = nocraft
        self.nohang = nohang
        self.timeout, self.logreq = timeout, logreq
        self.logresp, self.hexdump = logresp, hexdump
        self.http2_framedump = http2_framedump
        self.explain = explain
        self.logfp = logfp

        self.log = []
        self.logid = 0
        self.anchors = anchors

        self.settings = language.Settings(
            staticdir=self.staticdir
        )

        self.loglock = threading.Lock()

    def check_policy(self, req, settings):
        """
            A policy check that verifies the request size is within limits.
        """
        if self.nocraft:
            return "Crafting disabled.", None
        try:
            req = req.resolve(settings)
            l = req.maximum_length(settings)
        except language.FileAccessDenied:
            return "File access denied.", None
        if self.sizelimit and l > self.sizelimit:
            return "Response too large.", None
        pauses = [isinstance(i, language.actions.PauseAt) for i in req.actions]
        if self.nohang and any(pauses):
            return "Pauses have been disabled.", None
        return None, req

    def handle_client_connection(self, request, client_address):
        h = PathodHandler(
            request,
            client_address,
            self,
            self.logfp,
            self.settings,
            self.http2_framedump,
        )
        try:
            h.handle()
            h.finish()
        except TcpDisconnect:  # pragma: no cover
            log.write_raw(self.logfp, "Disconnect")
            self.add_log(
                dict(
                    type="error",
                    msg="Disconnect"
                )
            )
            return
        except TcpTimeout:
            log.write_raw(self.logfp, "Timeout")
            self.add_log(
                dict(
                    type="timeout",
                )
            )
            return

    def add_log(self, d):
        with self.loglock:
            d["id"] = self.logid
            self.log.insert(0, d)
            if len(self.log) > self.LOGBUF:
                self.log.pop()
            self.logid += 1
        return d["id"]

    def clear_log(self):
        with self.loglock:
            self.log = []

    def log_by_id(self, identifier):
        with self.loglock:
            for i in self.log:
                if i["id"] == identifier:
                    return i

    def get_log(self):
        with self.loglock:
            return self.log


def main(args):  # pragma: no cover
    ssloptions = SSLOptions(
        cn=args.cn,
        confdir=args.confdir,
        not_after_connect=args.ssl_not_after_connect,
        ciphers=args.ciphers,
        ssl_version=args.ssl_version,
        ssl_options=args.ssl_options,
        certs=args.ssl_certs,
        sans=args.sans,
    )

    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    log = logging.getLogger('pathod')
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        '%(asctime)s: %(message)s',
        datefmt='%d-%m-%y %H:%M:%S',
    )
    if args.logfile:
        fh = logging.handlers.WatchedFileHandler(args.logfile)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    if not args.daemonize:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        log.addHandler(sh)

    try:
        pd = Pathod(
            (args.address, args.port),
            craftanchor=args.craftanchor,
            ssl=args.ssl,
            ssloptions=ssloptions,
            staticdir=args.staticdir,
            anchors=args.anchors,
            sizelimit=args.sizelimit,
            nocraft=args.nocraft,
            nohang=args.nohang,
            timeout=args.timeout,
            logreq=args.logreq,
            logresp=args.logresp,
            hexdump=args.hexdump,
            http2_framedump=args.http2_framedump,
            explain=args.explain,
            webdebug=args.webdebug
        )
    except PathodError as v:
        print("Error: %s" % v, file=sys.stderr)
        sys.exit(1)
    except language.FileAccessDenied as v:
        print("Error: %s" % v, file=sys.stderr)

    if args.daemonize:
        utils.daemonize()

    try:
        print("%s listening on %s" % (
            version.PATHOD,
            repr(pd.address)
        ))
        pd.serve_forever()
    except KeyboardInterrupt:
        pass
