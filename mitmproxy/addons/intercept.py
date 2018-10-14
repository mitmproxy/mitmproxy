import typing

from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import ctx


class Intercept:
    def __init__(self):
        self.filt = None

    def load(self, loader):
        loader.add_option(
            "intercept_active", bool, False,
            "Intercept toggle"
        )

        loader.add_option(
            "intercept", typing.Optional[str], None,
            "Intercept filter expression."
        )

    def configure(self, updated):
        if "intercept" in updated:
            if not ctx.options.intercept:
                self.filt = None
                ctx.options.intercept_active = False
                return
            self.filt = flowfilter.parse(ctx.options.intercept)
            if not self.filt:
                raise exceptions.OptionsError(
                    "Invalid interception filter: %s" % ctx.options.intercept
                )
            ctx.options.intercept_active = True

    def process_flow(self, f):
        if self.filt:
            should_intercept = all([
                self.filt(f),
                not f.request.is_replay,
            ])
            if should_intercept and ctx.options.intercept_active:
                f.intercept()

    # Handlers

    def request(self, f):
        self.process_flow(f)

    def response(self, f):
        self.process_flow(f)
