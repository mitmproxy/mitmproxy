import urllib, pprint
import tornado.web, tornado.template, tornado.ioloop, tornado.httpserver
import rparse, utils

class _Page(tornado.web.RequestHandler):
    def render(self, name, **kwargs):
        b = self.application.templates.load(name + ".html").generate(**kwargs)
        self.write(b)


class Index(_Page):
    name = "index"
    section = "main"
    def get(self):
        self.render(self.name, section=self.section)


class Preview(_Page):
    name = "preview"
    section = "main"
    def get(self):
        self.render(self.name, section=self.section)


class Help(_Page):
    name = "help"
    section = "help"
    def get(self):
        self.render(self.name, section=self.section)


class Log(_Page):
    name = "log"
    section = "log"
    def get(self):
        self.render(self.name, section=self.section)


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
        self.templates = tornado.template.Loader(utils.data.path("templates"))
        self.appsettings = settings
        tornado.web.Application.__init__(
            self,
            [
                (r"/", Index),
                (r"/log", Log),
                (r"/help", Help),
                (r"/preview", Preview),
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


# begin nocover
def run(application, port, ssl_options):
    http_server = tornado.httpserver.HTTPServer(
        application,
        ssl_options=ssl_options
    )
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

