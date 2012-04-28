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
    anchor = "/p/"
    def __init__(self, application, request, **settings):
        self.application, self.request, self.settings = application, request, settings
        spec = urllib.unquote(self.request.uri)[len(self.anchor):]
        try:
            self.response = rparse.parse(self.settings, spec)
        except rparse.ParseException, v:
            self.response = rparse.InternalResponse(
                800,
                "Error parsing response spec: %s\n"%v.msg + v.marked()
            )

    def _execute(self, transforms, *args, **kwargs):
        self.response.render(self.request)


class PathodApp(tornado.web.Application):
    def __init__(self, **settings):
        self.templates = tornado.template.Loader(utils.data.path("templates"))
        tornado.web.Application.__init__(
            self,
            [
                (r"/", Index),
                (r"/log", Log),
                (r"/help", Help),
                (r"/preview", Preview),
                (r"/p/.*", Pathod, settings),
            ],
            static_path = utils.data.path("static"),
            template_path = utils.data.path("templates"),
            debug=True
        )


# begin nocover
def run(application, port, ssl_options):
    http_server = tornado.httpserver.HTTPServer(
        application,
        ssl_options=ssl_options
    )
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

