import typing

from mitmproxy import flow, flowfilter
from mitmproxy import exceptions
from mitmproxy import ctx


class Intercept:
    filt: typing.Optional[flowfilter.TFilter] = None

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
            if ctx.options.intercept:
                try:
                    self.filt = flowfilter.parse(ctx.options.intercept)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
                ctx.options.intercept_active = True
            else:
                self.filt = None
                ctx.options.intercept_active = False

    def should_intercept(self, f: flow.Flow) -> bool:
        return bool(
                ctx.options.intercept_active
                and self.filt
                and self.filt(f)
                and not f.is_replay
        )

    def process_flow(self, f: flow.Flow) -> None:
        if self.should_intercept(f):
            f.intercept()

    # Handlers

    def request(self, f):
        self.process_flow(f)

    def response(self, f):
        self.process_flow(f)

    def tcp_message(self, f):
        self.process_flow(f)
