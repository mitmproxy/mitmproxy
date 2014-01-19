import urllib, threading, re, logging
from netlib import tcp, http, wsgi, certutils
import netlib.utils
import version, app, language, utils

logger = logging.getLogger('pathod')

class PathodError(Exception): pass


class SSLOptions:
    def __init__(self, certfile=None, keyfile=None, not_after_connect=None, request_client_cert=False):
        self.keyfile = keyfile or utils.data.path("resources/server.key")
        self.certfile = certfile or utils.data.path("resources/server.crt")
        self.cert = certutils.SSLCert.from_pem(file(self.certfile, "rb").read())
        self.not_after_connect = not_after_connect
        self.request_client_cert = request_client_cert


class PathodHandler(tcp.BaseHandler):
    wbufsize = 0
    sni = None
    def info(self, s):
        logger.info("%s:%s: %s"%(self.client_address[0], self.client_address[1], str(s)))

    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def serve_crafted(self, crafted, request_log):
        c = self.server.check_policy(crafted, self.server.request_settings)
        if c:
            err = language.make_error_response(c)
            language.serve(err, self.wfile, self.server.request_settings)
            log = dict(
                type = "error",
                msg = c
            )
            return False, log

        if self.server.explain and not isinstance(crafted, language.PathodErrorResponse):
            crafted = crafted.freeze(self.server.request_settings, None)
            self.info(">> Spec: %s"%crafted.spec())
        response_log = language.serve(crafted, self.wfile, self.server.request_settings, None)
        log = dict(
                type = "crafted",
                request=request_log,
                response=response_log
            )
        if response_log["disconnect"]:
            return False, log
        return True, log

    def handle_request(self):
        """
            Returns a (again, log) tuple.

            again: True if request handling should continue.
            log: A dictionary, or None
        """
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            # Normal termination
            return False, None

        m = utils.MemBool()
        if m(http.parse_init_connect(line)):
            headers = http.read_headers(self.rfile)
            self.wfile.write(
                        'HTTP/1.1 200 Connection established\r\n' +
                        ('Proxy-agent: %s\r\n'%version.NAMEVERSION) +
                        '\r\n'
                        )
            self.wfile.flush()
            if not self.server.ssloptions.not_after_connect:
                try:
                    self.convert_to_ssl(
                        self.server.ssloptions.cert,
                        self.server.ssloptions.keyfile,
                        handle_sni = self.handle_sni,
                        request_client_cert = self.server.ssloptions.request_client_cert
                    )
                except tcp.NetLibError, v:
                    s = str(v)
                    self.info(s)
                    return False, dict(type = "error", msg = s)
            return True, None
        elif m(http.parse_init_proxy(line)):
            method, _, _, _, path, httpversion = m.v
        elif m(http.parse_init_http(line)):
            method, path, httpversion = m.v
        else:
            s = "Invalid first line: %s"%repr(line)
            self.info(s)
            return False, dict(type = "error", msg = s)

        headers = http.read_headers(self.rfile)
        if headers is None:
            s = "Invalid headers"
            self.info(s)
            return False, dict(type = "error", msg = s)

        clientcert = None
        if self.clientcert:
            clientcert = dict(
                cn = self.clientcert.cn,
                subject = self.clientcert.subject,
                serial = self.clientcert.serial,
                notbefore = self.clientcert.notbefore.isoformat(),
                notafter = self.clientcert.notafter.isoformat(),
                keyinfo = self.clientcert.keyinfo,
            )

        request_log = dict(
            path = path,
            method = method,
            headers = headers.lst,
            httpversion = httpversion,
            sni = self.sni,
            remote_address = self.client_address,
            clientcert = clientcert
        )

        try:
            content = http.read_http_body(
                        self.rfile, headers, None, True
                    )
        except http.HttpError, s:
            s = str(s)
            self.info(s)
            return False, dict(type = "error", msg = s)

        for i in self.server.anchors:
            if i[0].match(path):
                self.info("crafting anchor: %s"%path)
                aresp = language.parse_response(self.server.request_settings, i[1])
                return self.serve_crafted(aresp, request_log)

        if not self.server.nocraft and path.startswith(self.server.craftanchor):
            spec = urllib.unquote(path)[len(self.server.craftanchor):]
            self.info("crafting spec: %s"%spec)
            try:
                crafted = language.parse_response(self.server.request_settings, spec)
            except language.ParseException, v:
                self.info("Parse error: %s"%v.msg)
                crafted = language.make_error_response(
                        "Parse Error",
                        "Error parsing response spec: %s\n"%v.msg + v.marked()
                    )
            return self.serve_crafted(crafted, request_log)
        elif self.server.noweb:
            crafted = language.make_error_response("Access Denied")
            language.serve(crafted, self.wfile, self.server.request_settings)
            return False, dict(type = "error", msg="Access denied: web interface disabled")
        else:
            self.info("app: %s %s"%(method, path))
            cc = wsgi.ClientConn(self.client_address)
            req = wsgi.Request(cc, "http", method, path, headers, content)
            sn = self.connection.getsockname()
            a = wsgi.WSGIAdaptor(
                self.server.app,
                sn[0],
                self.server.port,
                version.NAMEVERSION
            )
            a.serve(req, self.wfile)
            return True, None

    def _log_bytes(self, header, data, hexdump):
        s = []
        if hexdump:
            s.append("%s (hex dump):"%header)
            for line in netlib.utils.hexdump(data):
                s.append("\t%s %s %s"%line)
        else:
            s.append("%s (unprintables escaped):"%header)
            s.append(netlib.utils.cleanBin(data))
        self.info("\n".join(s))

    def handle(self):
        if self.server.ssl:
            try:
                self.convert_to_ssl(
                    self.server.ssloptions.cert,
                    self.server.ssloptions.keyfile,
                    handle_sni = self.handle_sni,
                    request_client_cert = self.server.ssloptions.request_client_cert
                )
            except tcp.NetLibError, v:
                s = str(v)
                self.server.add_log(
                    dict(
                        type = "error",
                        msg = s
                    )
                )
                self.info(s)
                return
        self.settimeout(self.server.timeout)
        while not self.finished:
            if self.server.logreq:
                self.rfile.start_log()
            if self.server.logresp:
                self.wfile.start_log()
            again, log = self.handle_request()
            if log:
                if self.server.logreq:
                    log["request_bytes"] = self.rfile.get_log().encode("string_escape")
                    self._log_bytes("Request", log["request_bytes"], self.server.hexdump)
                if self.server.logresp:
                    log["response_bytes"] = self.wfile.get_log().encode("string_escape")
                    self._log_bytes("Response", log["response_bytes"], self.server.hexdump)
                self.server.add_log(log)
            if not again:
                return


class Pathod(tcp.TCPServer):
    LOGBUF = 500
    def __init__(   self,
                    addr, ssl=False, ssloptions=None, craftanchor="/p/", staticdir=None, anchors=None,
                    sizelimit=None, noweb=False, nocraft=False, noapi=False, nohang=False,
                    timeout=None, logreq=False, logresp=False, explain=False, hexdump=False
                ):
        """
            addr: (address, port) tuple. If port is 0, a free port will be
            automatically chosen.
            ssloptions: an SSLOptions object.
            craftanchor: string specifying the path under which to anchor response generation.
            staticdir: path to a directory of static resources, or None.
            anchors: A list of (regex, spec) tuples, or None.
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
        self.noweb, self.nocraft, self.noapi, self.nohang = noweb, nocraft, noapi, nohang
        self.timeout, self.logreq, self.logresp, self.hexdump = timeout, logreq, logresp, hexdump
        self.explain = explain

        self.app = app.make_app(noapi)
        self.app.config["pathod"] = self
        self.log = []
        self.logid = 0
        self.anchors = []
        if anchors:
            for i in anchors:
                try:
                    arex = re.compile(i[0])
                except re.error:
                    raise PathodError("Invalid regex in anchor: %s"%i[0])
                try:
                    language.parse_response(self.request_settings, i[1])
                except language.ParseException, v:
                    raise PathodError("Invalid page spec in anchor: '%s', %s"%(i[1], str(v)))
                self.anchors.append((arex, i[1]))

    def check_policy(self, req, settings):
        """
            A policy check that verifies the request size is withing limits.
        """
        try:
            l = req.maximum_length(settings)
        except language.FileAccessDenied:
            return "File access denied."
        if self.sizelimit and l > self.sizelimit:
            return "Response too large."
        if self.nohang and any([isinstance(i, language.PauseAt) for i in req.actions]):
            return "Pauses have been disabled."
        return False

    @property
    def request_settings(self):
        return dict(
            staticdir = self.staticdir
        )

    def handle_connection(self, request, client_address):
        h = PathodHandler(request, client_address, self)
        try:
            h.handle()
            h.finish()
        except tcp.NetLibDisconnect: # pragma: no cover
            h.info("Disconnect")
            self.add_log(
                dict(
                    type = "error",
                    msg = "Disconnect"
                )
            )
            return
        except tcp.NetLibTimeout:
            h.info("Timeout")
            self.add_log(
                dict(
                    type = "timeout",
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
