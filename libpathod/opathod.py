import urllib, pprint
import tornado.web, tornado.template, tornado.ioloop, tornado.httpserver
import rparse, utils, version


class Pathod(object):
    def __init__(self, spec, application, request, **settings):
        self.application, self.request, self.settings = application, request, settings
        try:
            self.response = rparse.parse(self.settings, spec)
        except rparse.ParseException, v:
            self.response = rparse.InternalResponse(
                800,
                "Error parsing response spec: %s\n"%v.msg + v.marked()
            )

    def _execute(self, transforms, *args, **kwargs):
        d = self.response.serve(self.request)
        d["request"] = dict(
            path = self.request.path,
            method = self.request.method,
            headers = self.request.headers,
            host = self.request.host,
            protocol = self.request.protocol,
            remote_address = self.request.connection.address,
            full_url = self.request.full_url(),
            query = self.request.query,
            version = self.request.version,
            uri = self.request.uri,
        )
        self.application.add_log(d)


class RequestPathod(Pathod):
    anchor = "/p/"
    def __init__(self, application, request, **settings):
        spec = urllib.unquote(request.uri)[len(self.anchor):]
        Pathod.__init__(self, spec, application, request, **settings)


class PathodApp(tornado.web.Application):
    LOGBUF = 500
    def __init__(self, **settings):
        self.appsettings = settings
        tornado.web.Application.__init__(
            self,
            [
                (r"/", Index),
                (r"/log", Log),
                (r"/log/clear", ClearLog),
                (r"/log/([0-9]+)", OneLog),
                (r"/help", Help),
                (r"/preview", Preview),
                (r"/api/shutdown", APIShutdown),
                (r"/api/info", APIInfo),
                (r"/api/log", APILog),
                (r"/api/log/clear", APILogClear),
                (r"/p/.*", RequestPathod, settings),
            ],
            static_path = utils.data.path("static"),
            template_path = utils.data.path("templates"),
            debug=True
        )
        self.log = []
        self.logid = 0

    def add_anchor(self, pattern, spec):
        """
            Anchors are added to the beginning of the handlers.
        """
        # We assume we have only one host...
        l = self.handlers[0][1]
        class FixedPathod(Pathod):
            def __init__(self, application, request, **settings):
                Pathod.__init__(self, spec, application, request, **settings)
        FixedPathod.spec = spec
        FixedPathod.pattern = pattern
        l.insert(0, tornado.web.URLSpec(pattern, FixedPathod, self.appsettings))

    def get_anchors(self):
        """
            Anchors are added to the beginning of the handlers.
        """
        l = self.handlers[0][1]
        a = []
        for i in l:
            if i.handler_class.__name__ == "FixedPathod":
                a.append(
                    (
                        i.handler_class.pattern,
                        i.handler_class.spec
                    )
                )
        return a

    def remove_anchor(self, pattern, spec):
        """
            Anchors are added to the beginning of the handlers.
        """
        l = self.handlers[0][1]
        for i, h in enumerate(l):
            if h.handler_class.__name__ == "FixedPathod":
                if (h.handler_class.pattern, h.handler_class.spec) == (pattern, spec):
                    del l[i]
                    return

    def add_log(self, d):
        d["id"] = self.logid
        self.log.insert(0, d)
        if len(self.log) > self.LOGBUF:
            self.log.pop()
        self.logid += 1

    def log_by_id(self, id):
        for i in self.log:
            if i["id"] == id:
                return i

    def clear_log(self):
        self.log = []

    def get_log(self):
        return self.log


def make_app(staticdir=None, anchors=()):
    """
        staticdir: A directory for static assets referenced in response patterns.
        anchors: A sequence of strings of the form "pattern=pagespec"
    """
    settings = dict(
        staticdir=staticdir
    )
    application = PathodApp(**settings)
    for i in anchors:
        rex, spec = utils.parse_anchor_spec(i, settings)
        application.add_anchor(rex, spec)
    return application


def make_server(application, port, address, ssl_options):
    """
        Returns a (server, port) tuple.

        The returned port will match the passed port, unless the passed port
        was 0. In that case, an arbitrary empty port will be bound to, and this
        new port will be returned.
    """
    http_server = tornado.httpserver.HTTPServer(
        application,
        ssl_options=ssl_options
    )
    http_server.listen(port, address)
    port = port
    for i in http_server._sockets.values():
        sn = i.getsockname()
        if sn[0] == address:
            port = sn[1]
    return http_server, port


# begin nocover
def run(server):
    tornado.ioloop.IOLoop.instance().start()
    server.stop()


class APILog(tornado.web.RequestHandler):
    def get(self):
        self.write(
            dict(
                d = self.application.get_log()
            )
        )


class APILogClear(tornado.web.RequestHandler):
    def post(self):
        self.application.clear_log()
        self.write("OK")


class APIShutdown(tornado.web.RequestHandler):
    def post(self):
        tornado.ioloop.IOLoop.instance().stop()
        self.write("OK")


class APIInfo(tornado.web.RequestHandler):
    def get(self):
        self.write(
            dict(
                version = version.IVERSION
            )
        )


class _Page(tornado.web.RequestHandler):
    def render(self, name, **kwargs):
        tornado.web.RequestHandler.render(self, name + ".html", **kwargs)


class Index(_Page):
    name = "index"
    section = "main"
    def get(self):
        self.render(self.name, section=self.section, spec="")


class Preview(_Page):
    name = "preview"
    section = "main"
    SANITY = 1024*1024
    def get(self):
        spec = self.get_argument("spec", None)
        args = dict(
            spec = spec,
            section = self.section,
            syntaxerror = None,
            error = None
        )
        try:
            r = rparse.parse(self.application.settings, spec)
        except rparse.ParseException, v:
            args["syntaxerror"] = str(v)
            args["marked"] = v.marked()
            return self.render(self.name, **args)
        if r.length() > self.SANITY:
            error = "Refusing to preview a response of %s bytes. This is for your own good."%r.length()
            args["error"] = error
        else:
            d = utils.DummyRequest()
            r.serve(d)
            args["output"] = d.getvalue()
        self.render(self.name, **args)


class Help(_Page):
    name = "help"
    section = "help"
    def get(self):
        self.render(self.name, section=self.section)


class Log(_Page):
    name = "log"
    section = "log"
    def get(self):
        self.render(self.name, section=self.section, log=self.application.log)


class OneLog(_Page):
    name = "onelog"
    section = "log"
    def get(self, lid):
        l = pprint.pformat(self.application.log_by_id(int(lid)))
        self.render(self.name, section=self.section, alog=l, lid=lid)


class ClearLog(_Page):
    def post(self):
        self.application.clear_logs()
        self.redirect("/log")
