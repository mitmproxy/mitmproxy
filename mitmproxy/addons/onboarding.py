from mitmproxy.addons import wsgiapp
from mitmproxy.addons.onboardingapp import app


class Onboarding(wsgiapp.WSGIApp):
    def __init__(self):
        super().__init__(app.Adapter(app.application), None, None)
        self.enabled = False

    def configure(self, options, updated):
        self.host = options.app_host
        self.port = options.app_port
        self.enabled = options.app

    def request(self, f):
        if self.enabled:
            super().request(f)
