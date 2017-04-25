from mitmproxy.addons import wsgiapp
from mitmproxy.addons.onboardingapp import app
from mitmproxy import ctx


class Onboarding(wsgiapp.WSGIApp):
    name = "onboarding"

    def __init__(self):
        super().__init__(app.Adapter(app.application), None, None)

    def configure(self, options, updated):
        self.host = options.onboarding_host
        self.port = options.onboarding_port

    def request(self, f):
        if ctx.options.onboarding:
            super().request(f)
