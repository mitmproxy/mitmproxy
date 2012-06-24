import urllib, threading, re
from netlib import tcp, http, odict, wsgi
import version, app, rparse

class PathodError(Exception): pass


class PathodHandler(tcp.BaseHandler):
    def handle(self):
        if self.server.ssloptions:
            self.convert_to_ssl(
                self.server.ssloptions["certfile"],
                self.server.ssloptions["keyfile"],
            )

        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            return None

        method, path, httpversion = http.parse_init_http(line)
        headers = odict.ODictCaseless(http.read_headers(self.rfile))
        content = http.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, None
                )

        crafted = None
        for i in self.server.anchors:
            if i[0].match(path):
                crafted = i[1]

        if not crafted and path.startswith(self.server.prefix):
            spec = urllib.unquote(path)[len(self.server.prefix):]
            try:
                crafted = rparse.parse_response(self.server.request_settings, spec)
            except rparse.ParseException, v:
                crafted = rparse.InternalResponse(
                    800,
                    "Error parsing response spec: %s\n"%v.msg + v.marked()
                )

        if crafted:
            ret = crafted.serve(self.wfile)
            if ret["disconnect"]:
                self.finish()
            ret["request"] = dict(
                path = path,
                method = method,
                headers = headers.lst,
                #remote_address = self.request.connection.address,
                #full_url = self.request.full_url(),
                #query = self.request.query,
                httpversion = httpversion,
                #uri = self.request.uri,
            )
            self.server.add_log(ret)
        else:
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


class Pathod(tcp.TCPServer):
    LOGBUF = 500
    def __init__(self, addr, ssloptions=None, prefix="/p/", staticdir=None, anchors=None):
        """
            addr: (address, port) tuple. If port is 0, a free port will be
            automatically chosen.
            ssloptions: a dictionary containing certfile and keyfile specifications.
            prefix: string specifying the prefix at which to anchor response generation.
            staticdir: path to a directory of static resources, or None.
            anchors: A list of (regex, spec) tuples, or None.
        """
        tcp.TCPServer.__init__(self, addr)
        self.ssloptions = ssloptions
        self.staticdir = staticdir
        self.prefix = prefix
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
                self.anchors.append((arex, aresp))

    @property
    def request_settings(self):
        return dict(
            staticdir = self.staticdir
        )

    def handle_connection(self, request, client_address):
        PathodHandler(request, client_address, self)

    def add_log(self, d):
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
