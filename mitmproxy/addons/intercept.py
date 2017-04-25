from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import ctx


class Intercept:
    def __init__(self):
        self.filt = None

    def configure(self, updated):
        if "intercept" in updated:
            if not ctx.options.intercept:
                self.filt = None
                return
            self.filt = flowfilter.parse(ctx.options.intercept)
            if not self.filt:
                raise exceptions.OptionsError(
                    "Invalid interception filter: %s" % ctx.options.intercept
                )

    def process_flow(self, f):
        if self.filt:
            should_intercept = all([
                self.filt(f),
                not f.request.is_replay,
            ])
            if should_intercept:
                f.intercept()

    # Handlers

    def request(self, f):
        self.process_flow(f)

    def response(self, f):
        self.process_flow(f)
