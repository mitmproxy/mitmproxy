import copy
import logging
import os
import sys
import threading
import urllib
import re

from netlib import tcp, http, wsgi, certutils, websockets

from . import version, app, language, utils, log
import language.http
import language.actions


DEFAULT_CERT_DOMAIN = "pathod.net"
CONFDIR = "~/.mitmproxy"
CERTSTORE_BASENAME = "mitmproxy"
CA_CERT_NAME = "mitmproxy-ca.pem"
DEFAULT_ANCHOR = r"/p/?"

logger = logging.getLogger('pathod')


class PathodError(Exception):
    pass


class SSLOptions:
    def __init__(
        self,
        confdir=CONFDIR,
        cn=None,
        sans=(),
        not_after_connect=None,
        request_client_cert=False,
        sslversion=tcp.SSLv23_METHOD,
        ciphers=None,
        certs=None
    ):
        self.confdir = confdir
        self.cn = cn
        self.certstore = certutils.CertStore.from_store(
            os.path.expanduser(confdir),
            CERTSTORE_BASENAME
        )
        for i in certs or []:
            self.certstore.add_cert_file(*i)
        self.not_after_connect = not_after_connect
        self.request_client_cert = request_client_cert
        self.ciphers = ciphers
        self.sslversion = sslversion
        self.sans = sans

    def get_cert(self, name):
        if self.cn:
            name = self.cn
        elif not name:
            name = DEFAULT_CERT_DOMAIN
        return self.certstore.get_cert(name, self.sans)


class PathodHandler(tcp.BaseHandler):
    wbufsize = 0
    sni = None

    def __init__(self, connection, address, server, logfp, settings):
        self.logfp = logfp
        tcp.BaseHandler.__init__(self, connection, address, server)
        self.settings = copy.copy(settings)

    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def serve_crafted(self, crafted):
        error, crafted = self.server.check_policy(
            crafted, self.settings
        )
        if error:
            err = language.http.make_error_response(error)
            language.serve(err, self.wfile, self.settings)
            return None, dict(
                type="error",
                msg = error
            )

        if self.server.explain and not isinstance(
                crafted,
                language.http.PathodErrorResponse
        ):
            crafted = crafted.freeze(self.settings)
            log.write(self.logfp, ">> Spec: %s" % crafted.spec())
        response_log = language.serve(
            crafted,
            self.wfile,
            self.settings
        )
        if response_log["disconnect"]:
            return None, response_log
        return self.handle_http_request, response_log

    def handle_websocket(self):
        lr = self.rfile if self.server.logreq else None
        lw = self.wfile if self.server.logresp else None
        with log.Log(self.logfp, self.server.hexdump, lr, lw) as lg:
            while True:
                try:
                    frm = websockets.Frame.from_file(self.rfile)
                    retlog = dict(
                        type="wsframe",
                        frame=dict(
                        ),
                        cipher=None,
                    )
                    self.addlog(retlog)
                    break
                except tcp.NetLibTimeout: # pragma: no cover
                    pass
            lg(frm.human_readable())
        return self.handle_websocket, None

    def handle_http_connect(self, connect, lg):
        """
            Handle a CONNECT request.
        """
        headers = http.read_headers(self.rfile)
        self.wfile.write(
            'HTTP/1.1 200 Connection established\r\n' +
            ('Proxy-agent: %s\r\n' % version.NAMEVERSION) +
            '\r\n'
        )
        self.wfile.flush()
        if not self.server.ssloptions.not_after_connect:
            try:
                cert, key, chain_file = self.server.ssloptions.get_cert(
                    connect[0]
                )
                self.convert_to_ssl(
                    cert,
                    key,
                    handle_sni=self.handle_sni,
                    request_client_cert=self.server.ssloptions.request_client_cert,
                    cipher_list=self.server.ssloptions.ciphers,
                    method=self.server.ssloptions.sslversion,
                )
            except tcp.NetLibError as v:
                s = str(v)
                lg(s)
                return None, dict(type="error", msg=s)
        return self.handle_http_request, None

    def handle_http_app(self, method, path, headers, content, lg):
        """
            Handle a request to the built-in app.
        """
        if self.server.noweb:
            crafted = language.http.make_error_response("Access Denied")
            language.serve(crafted, self.wfile, self.settings)
            return None, dict(
                type="error",
                msg="Access denied: web interface disabled"
            )
        lg("app: %s %s" % (method, path))
        req = wsgi.Request("http", method, path, headers, content)
        flow = wsgi.Flow(self.address, req)
        sn = self.connection.getsockname()
        a = wsgi.WSGIAdaptor(
            self.server.app,
            sn[0],
            self.server.address.port,
            version.NAMEVERSION
        )
        a.serve(flow, self.wfile)
        return self.handle_http_request, None

    def handle_http_request(self):
        """
            Returns a (handler, log) tuple.

            handler: Handler for the next request, or None to disconnect
            log: A dictionary, or None
        """
        lr = self.rfile if self.server.logreq else None
        lw = self.wfile if self.server.logresp else None
        with log.Log(self.logfp, self.server.hexdump, lr, lw) as lg:
            line = http.get_request_line(self.rfile)
            if not line:
                # Normal termination
                return None, None

            m = utils.MemBool()
            if m(http.parse_init_connect(line)):
                return self.handle_http_connect(m.v, lg)
            elif m(http.parse_init_proxy(line)):
                method, _, _, _, path, httpversion = m.v
            elif m(http.parse_init_http(line)):
                method, path, httpversion = m.v
            else:
                s = "Invalid first line: %s" % repr(line)
                lg(s)
                return None, dict(type="error", msg=s)

            headers = http.read_headers(self.rfile)
            if headers is None:
                s = "Invalid headers"
                lg(s)
                return None, dict(type="error", msg=s)

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
                request=dict(
                    path=path,
                    method=method,
                    headers=headers.lst,
                    httpversion=httpversion,
                    sni=self.sni,
                    remote_address=self.address(),
                    clientcert=clientcert,
                ),
                cipher=None,
            )
            if self.ssl_established:
                retlog["cipher"] = self.get_current_cipher()

            try:
                content = http.read_http_body(
                    self.rfile, headers, None,
                    method, None, True
                )
            except http.HttpError as s:
                s = str(s)
                lg(s)
                return None, dict(type="error", msg=s)

            m = utils.MemBool()
            websocket_key = websockets.check_client_handshake(headers)
            self.settings.websocket_key = websocket_key

            # If this is a websocket initiation, we respond with a proper
            # server response, unless over-ridden.
            if websocket_key:
                anchor_spec = language.parse_pathod("ws")
            else:
                anchor_spec = None
            for i in self.server.anchors:
                if i[0].match(path):
                    anchor_spec = i[1]
                    break
            else:
                if m(self.server.craftanchor.match(path)):
                    spec = urllib.unquote(path)[len(m.v.group()):]
                    if spec:
                        try:
                            anchor_spec = language.parse_pathod(spec)
                        except language.ParseException as v:
                            lg("Parse error: %s" % v.msg)
                            anchor_spec = language.http.make_error_response(
                                "Parse Error",
                                "Error parsing response spec: %s\n" % (
                                    v.msg + v.marked()
                                )
                            )

            if anchor_spec:
                lg("crafting spec: %s" % anchor_spec)
                nexthandler, retlog["response"] = self.serve_crafted(
                    anchor_spec
                )
                if nexthandler and websocket_key:
                    return self.handle_websocket, retlog
                else:
                    return nexthandler, retlog
            else:
                return self.handle_http_app(method, path, headers, content, lg)

    def addlog(self, log):
        # FIXME: The bytes in the log should not be escaped. We do this at the
        # moment because JSON encoding can't handle binary data, and I don't
        # want to base64 everything.
        if self.server.logreq:
            bytes = self.rfile.get_log().encode("string_escape")
            log["request_bytes"] = bytes
        if self.server.logresp:
            bytes = self.wfile.get_log().encode("string_escape")
            log["response_bytes"] = bytes
        self.server.add_log(log)

    def handle(self):
        if self.server.ssl:
            try:
                cert, key, _ = self.server.ssloptions.get_cert(None)
                self.convert_to_ssl(
                    cert,
                    key,
                    handle_sni=self.handle_sni,
                    request_client_cert=self.server.ssloptions.request_client_cert,
                    cipher_list=self.server.ssloptions.ciphers,
                    method=self.server.ssloptions.sslversion,
                )
            except tcp.NetLibError as v:
                s = str(v)
                self.server.add_log(
                    dict(
                        type="error",
                        msg=s
                    )
                )
                log.write(self.logfp, s)
                return
        self.settimeout(self.server.timeout)
        handler = self.handle_http_request
        while not self.finished:
            handler, l = handler()
            if l:
                self.addlog(l)
            if not handler:
                return


class Pathod(tcp.TCPServer):
    LOGBUF = 500

    def __init__(
        self,
        addr,
        ssl=False,
        ssloptions=None,
        craftanchor=re.compile(DEFAULT_ANCHOR),
        staticdir=None,
        anchors=(),
        sizelimit=None,
        noweb=False,
        nocraft=False,
        noapi=False,
        nohang=False,
        timeout=None,
        logreq=False,
        logresp=False,
        explain=False,
        hexdump=False,
        webdebug=False,
        logfp=sys.stdout,
    ):
        """
            addr: (address, port) tuple. If port is 0, a free port will be
            automatically chosen.
            ssloptions: an SSLOptions object.
            craftanchor: string specifying the path under which to anchor
            response generation.
            staticdir: path to a directory of static resources, or None.
            anchors: List of (regex object, language.Request object) tuples, or
            None.
            sizelimit: Limit size of served data.
            nocraft: Disable response crafting.
            noapi: Disable the API.
            nohang: Disable pauses.
        """
        tcp.TCPServer.__init__(self, addr)
        self.ssl = ssl
        self.ssloptions = ssloptions or SSLOptions()
        self.staticdir = staticdir
        self.craftanchor = craftanchor
        self.sizelimit = sizelimit
        self.noweb, self.nocraft = noweb, nocraft
        self.noapi, self.nohang = noapi, nohang
        self.timeout, self.logreq = timeout, logreq
        self.logresp, self.hexdump = logresp, hexdump
        self.explain = explain
        self.logfp = logfp

        self.app = app.make_app(noapi, webdebug)
        self.app.config["pathod"] = self
        self.log = []
        self.logid = 0
        self.anchors = anchors

        self.settings = language.Settings(
            staticdir = self.staticdir
        )

    def check_policy(self, req, settings):
        """
            A policy check that verifies the request size is withing limits.
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
            self.settings
        )
        try:
            h.handle()
            h.finish()
        except tcp.NetLibDisconnect:  # pragma: no cover
            log.write(self.logfp, "Disconnect")
            self.add_log(
                dict(
                    type="error",
                    msg="Disconnect"
                )
            )
            return
        except tcp.NetLibTimeout:
            log.write(self.logfp, "Timeout")
            self.add_log(
                dict(
                    type="timeout",
                )
            )
            return

    def add_log(self, d):
        if not self.noapi:
            lock = threading.Lock()
            with lock:
                d["id"] = self.logid
                self.log.insert(0, d)
                if len(self.log) > self.LOGBUF:
                    self.log.pop()
                self.logid += 1
            return d["id"]

    def clear_log(self):
        lock = threading.Lock()
        with lock:
            self.log = []

    def log_by_id(self, id):
        for i in self.log:
            if i["id"] == id:
                return i

    def get_log(self):
        return self.log


def main(args):  # pragma: nocover
    ssloptions = SSLOptions(
        cn = args.cn,
        confdir = args.confdir,
        not_after_connect = args.ssl_not_after_connect,
        ciphers = args.ciphers,
        sslversion = utils.SSLVERSIONS[args.sslversion],
        certs = args.ssl_certs,
        sans = args.sans
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
            craftanchor = args.craftanchor,
            ssl = args.ssl,
            ssloptions = ssloptions,
            staticdir = args.staticdir,
            anchors = args.anchors,
            sizelimit = args.sizelimit,
            noweb = args.noweb,
            nocraft = args.nocraft,
            noapi = args.noapi,
            nohang = args.nohang,
            timeout = args.timeout,
            logreq = args.logreq,
            logresp = args.logresp,
            hexdump = args.hexdump,
            explain = args.explain,
            webdebug = args.webdebug
        )
    except PathodError as v:
        print >> sys.stderr, "Error: %s" % v
        sys.exit(1)
    except language.FileAccessDenied as v:
        print >> sys.stderr, "Error: %s" % v

    if args.daemonize:
        utils.daemonize()

    try:
        print "%s listening on %s:%s" % (
            version.NAMEVERSION,
            pd.address.host,
            pd.address.port
        )
        pd.serve_forever()
    except KeyboardInterrupt:
        pass
