from mitmproxy.addons import wsgiapp
from mitmproxy.addons.onboardingapp import app


class Onboarding(wsgiapp.WSGIApp):
    name = "onboarding"

    def __init__(self):
        super().__init__(app.Adapter(app.application), None, None)
        self.enabled = False

    def configure(self, options, updated):
        self.host = options.onboarding_host
        self.port = options.onboarding_port
        self.enabled = options.onboarding

    def request(self, f):
        if self.enabled:
            super().request(f)
