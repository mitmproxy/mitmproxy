import urllib, threading, re, logging, socket, sys
from netlib import tcp, http, odict, wsgi
import version, app, rparse

logger = logging.getLogger('pathod')


class PathodError(Exception): pass


class PathodHandler(tcp.BaseHandler):
    wbufsize = 0
    sni = None
    def info(self, s):
        logger.info("%s:%s: %s"%(self.client_address[0], self.client_address[1], str(s)))

    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def serve_crafted(self, crafted, request_log):
        response_log = crafted.serve(self.wfile, self.server.check_policy)
        self.server.add_log(
            dict(
                type = "crafted",
                request=request_log,
                response=response_log
            )
        )
        if response_log["disconnect"]:
            return False
        return True

    def handle_request(self):
        """
            Returns True if handling should continue.
        """
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            return

        parts = http.parse_init_http(line)
        if not parts:
            s = "Invalid first line: %s"%repr(line)
            self.info(s)
            self.server.add_log(
                dict(
                    type = "error",
                    msg = s
                )
            )
            return

        method, path, httpversion = parts
        headers = http.read_headers(self.rfile)
        if headers is None:
            s = "Invalid headers"
            self.info(s)
            self.server.add_log(
                dict(
                    type = "error",
                    msg = s
                )
            )
            return

        request_log = dict(
            path = path,
            method = method,
            headers = headers.lst,
            httpversion = httpversion,
            sni = self.sni,
            remote_address = self.client_address,
        )

        try:
            content = http.read_http_body_request(
                        self.rfile, self.wfile, headers, httpversion, None
                    )
        except http.HttpError, s:
            s = str(s)
            self.info(s)
            self.server.add_log(
                dict(
                    type = "error",
                    msg = s
                )
            )
            return

        for i in self.server.anchors:
            if i[0].match(path):
                self.info("crafting anchor: %s"%path)
                aresp = rparse.parse_response(self.server.request_settings, i[1])
                return self.serve_crafted(aresp, request_log)

        if not self.server.nocraft and path.startswith(self.server.craftanchor):
            spec = urllib.unquote(path)[len(self.server.craftanchor):]
            self.info("crafting spec: %s"%spec)
            try:
                crafted = rparse.parse_response(self.server.request_settings, spec)
            except rparse.ParseException, v:
                self.info("Parse error: %s"%v.msg)
                crafted = rparse.PathodErrorResponse(
                        "Parse Error",
                        "Error parsing response spec: %s\n"%v.msg + v.marked()
                    )
            except rparse.FileAccessDenied:
                self.info("File access denied")
                crafted = rparse.PathodErrorResponse("Access Denied")
            return self.serve_crafted(crafted, request_log)
        elif self.server.noweb:
            crafted = rparse.PathodErrorResponse("Access Denied")
            crafted.serve(self.wfile, self.server.check_policy)
            return False
        else:
            self.info("app: %s %s"%(method, path))
            cc = wsgi.ClientConn(self.client_address)
            req = wsgi.Request(cc, "http", method, path, headers, content)
            sn = self.connection.getsockname()
            app = wsgi.WSGIAdaptor(
                self.server.app,
                sn[0],
                self.server.port,
                version.NAMEVERSION
            )
            app.serve(req, self.wfile)
            return True

    def handle(self):
        if self.server.ssloptions:
            try:
                self.convert_to_ssl(
                    self.server.ssloptions["certfile"],
                    self.server.ssloptions["keyfile"],
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

        while not self.finished:
            if not self.handle_request():
                return


class Pathod(tcp.TCPServer):
    LOGBUF = 500
    def __init__(   self,
                    addr, ssloptions=None, craftanchor="/p/", staticdir=None, anchors=None,
                    sizelimit=None, noweb=False, nocraft=False, noapi=False, nohang=False
                ):
        """
            addr: (address, port) tuple. If port is 0, a free port will be
            automatically chosen.
            ssloptions: a dictionary containing certfile and keyfile specifications.
            craftanchor: string specifying the path under which to anchor response generation.
            staticdir: path to a directory of static resources, or None.
            anchors: A list of (regex, spec) tuples, or None.
            sizelimit: Limit size of served data.
            nocraft: Disable response crafting.
            noapi: Disable the API.
            nohang: Disable pauses.
        """
        tcp.TCPServer.__init__(self, addr)
        self.ssloptions = ssloptions
        self.staticdir = staticdir
        self.craftanchor = craftanchor
        self.sizelimit = sizelimit
        self.noweb, self.nocraft, self.noapi, self.nohang = noweb, nocraft, noapi, nohang
        if not noapi:
            app.api()
        self.app = app.app
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
                    aresp = rparse.parse_response(self.request_settings, i[1])
                except rparse.ParseException, v:
                    raise PathodError("Invalid page spec in anchor: '%s', %s"%(i[1], str(v)))
                self.anchors.append((arex, i[1]))

    def check_policy(self, req, actions):
        """
            A policy check that verifies the request size is withing limits.
        """
        if self.sizelimit and req.effective_length(actions) > self.sizelimit:
            return "Response too large."
        if self.nohang and any([i[1] == "pause" for i in actions]):
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
