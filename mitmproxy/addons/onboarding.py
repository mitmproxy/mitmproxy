from mitmproxy.addons import wsgiapp
from mitmproxy.addons.onboardingapp import app
from mitmproxy import ctx

APP_HOST = "mitm.it"
APP_PORT = 80


class Onboarding(wsgiapp.WSGIApp):
    name = "onboarding"

    def __init__(self):
        super().__init__(app, None, None)

    def load(self, loader):
        loader.add_option(
            "onboarding", bool, True,
            "Toggle the mitmproxy onboarding app."
        )
        loader.add_option(
            "onboarding_host", str, APP_HOST,
            """
            Onboarding app domain. For transparent mode, use an IP when a DNS
            entry for the app domain is not present.
            """
        )
        loader.add_option(
            "onboarding_port", int, APP_PORT,
            "Port to serve the onboarding app from."
        )

    def configure(self, updated):
        self.host = ctx.options.onboarding_host
        self.port = ctx.options.onboarding_port
        app.config["CONFDIR"] = ctx.options.confdir

    def request(self, f):
        if ctx.options.onboarding:
            super().request(f)
