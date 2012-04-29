import urllib
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
        self.response.render(self.request)


class RequestPathod(Pathod):
    anchor = "/p/"
    def __init__(self, application, request, **settings):
        spec = urllib.unquote(request.uri)[len(self.anchor):]
        Pathod.__init__(self, spec, application, request, **settings)


class PathodApp(tornado.web.Application):
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
        l.insert(0, tornado.web.URLSpec(pattern, FixedPathod, self.appsettings))

    def get_anchors(self, pattern, spec):
        """
            Anchors are added to the beginning of the handlers.
        """
        pass

    def remove_anchor(self, pattern, spec):
        """
            Anchors are added to the beginning of the handlers.
        """
        pass


# begin nocover
def run(application, port, ssl_options):
    http_server = tornado.httpserver.HTTPServer(
        application,
        ssl_options=ssl_options
    )
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

