import urllib, threading
from netlib import tcp, protocol, odict, wsgi
import version, app, rparse


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

        method, path, httpversion = protocol.parse_init_http(line)
        headers = odict.ODictCaseless(protocol.read_headers(self.rfile))
        content = protocol.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, None
                )

        if path.startswith(self.server.prefix):
            spec = urllib.unquote(path)[len(self.server.prefix):]
            try:
                presp = rparse.parse({}, spec)
            except rparse.ParseException, v:
                presp = rparse.InternalResponse(
                    800,
                    "Error parsing response spec: %s\n"%v.msg + v.marked()
                )
            ret = presp.serve(self.wfile)
            if ret["disconnect"]:
                self.close()

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
        tcp.TCPServer.__init__(self, addr)
        self.ssloptions = ssloptions
        self.prefix = prefix
        self.app = app.app
        self.app.config["pathod"] = self
        self.log = []
        self.logid = 0

    @property
    def request_settings(self):
        return {}

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
