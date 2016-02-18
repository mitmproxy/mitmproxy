from __future__ import absolute_import
import os
import tornado.web
import tornado.wsgi
import tornado.template

from .. import utils
from ..proxy import config


loader = tornado.template.Loader(utils.pkg_data.path("onboarding/templates"))


class Adapter(tornado.wsgi.WSGIAdapter):
    # Tornado doesn't make the WSGI environment available to pages, so this
    # hideous monkey patch is the easiest way to get to the mitmproxy.master
    # variable.

    def __init__(self, application):
        self._application = application

    def application(self, request):
        request.master = self.environ["mitmproxy.master"]
        return self._application(request)

    def __call__(self, environ, start_response):
        self.environ = environ
        return tornado.wsgi.WSGIAdapter.__call__(
            self,
            environ,
            start_response
        )


class Index(tornado.web.RequestHandler):

    def get(self):
        t = loader.load("index.html")
        self.write(t.generate())


class PEM(tornado.web.RequestHandler):

    @property
    def filename(self):
        return config.CONF_BASENAME + "-ca-cert.pem"

    def get(self):
        p = os.path.join(self.request.master.server.config.cadir, self.filename)
        self.set_header("Content-Type", "application/x-x509-ca-cert")
        self.set_header(
            "Content-Disposition",
            "inline; filename={}".format(
                self.filename))

        with open(p, "rb") as f:
            self.write(f.read())


class P12(tornado.web.RequestHandler):

    @property
    def filename(self):
        return config.CONF_BASENAME + "-ca-cert.p12"

    def get(self):
        p = os.path.join(self.request.master.server.config.cadir, self.filename)
        self.set_header("Content-Type", "application/x-pkcs12")
        self.set_header(
            "Content-Disposition",
            "inline; filename={}".format(
                self.filename))

        with open(p, "rb") as f:
            self.write(f.read())


application = tornado.web.Application(
    [
        (r"/", Index),
        (r"/cert/pem", PEM),
        (r"/cert/p12", P12),
        (
            r"/static/(.*)",
            tornado.web.StaticFileHandler,
            {
                "path": utils.pkg_data.path("onboarding/static")
            }
        ),
    ],
    # debug=True
)
mapp = Adapter(application)
