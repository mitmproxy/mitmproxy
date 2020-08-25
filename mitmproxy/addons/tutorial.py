from mitmproxy.addons import asgiapp
from mitmproxy.addons.tutorialapp import app
from mitmproxy import ctx

APP_HOST = "tutorial.mitm.it"
APP_PORT = 80


class Tutorial(asgiapp.WSGIApp):
    name = "tutorial"

    def __init__(self):
        super().__init__(app, APP_HOST, APP_PORT)

    def load(self, loader):
        loader.add_option(
            "tutorial", bool, True,
            "Toggle the mitmproxy tutorial app."
        )
        loader.add_option(
            "tutorial_host", str, APP_HOST,
            """
            Tutorial app domain. For transparent mode, use an IP when a DNS
            entry for the app domain is not present.
            """
        )
        loader.add_option(
            "tutorial_port", int, APP_PORT,
            "Port to serve the tutorial app from."
        )

    def configure(self, updated):
        self.host = ctx.options.tutorial_host
        self.port = ctx.options.tutorial_port
        app.config["CONFDIR"] = ctx.options.confdir

    def request(self, f):
        if ctx.options.tutorial:
            super().request(f)
