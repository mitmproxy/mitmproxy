import urllib
import tornado.web
import rparse

class _Page(tornado.web.RequestHandler):
    def render(self, name, **kwargs):
        b = self.application.templates.load(name).generate(**kwargs)
        self.write(b)


class Index(_Page):
    def get(self):
        self.render("index.html", section="main")


class Preview(_Page):
    def get(self):
        self.render("index.html", section="main")


class Help(_Page):
    def get(self):
        self.render("help.html", section="help")


class Log(_Page):
    def get(self):
        self.render("log.html", section="log")


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
