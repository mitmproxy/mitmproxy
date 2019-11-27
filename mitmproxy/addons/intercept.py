import typing

from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import tcp


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
        is_replay = False
        if not isinstance(f, tcp.TCPViewEntry):
            is_replay = f.request.is_replay, 

        if self.filt:
            should_intercept = all([
                self.filt(f),
                not is_replay,
            ])
            if should_intercept and ctx.options.intercept_active:
                f.intercept()

    # Handlers

    def tcp_start(self, f):
        view = tcp.TCPFlowEntry(flow=f)
        self.process_flow(view)

    def tcp_message(self, f):
        view = tcp.TCPMessageEntry(flow=f, message=f.messages[-1])
        self.process_flow(view)

    def request(self, f):
        self.process_flow(f)

    def response(self, f):
        self.process_flow(f)
