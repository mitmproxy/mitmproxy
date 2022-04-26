from mitmproxy import ctx


class AntiComp:
    def load(self, loader):
        loader.add_option(
            "anticomp",
            bool,
            False,
            "Try to convince servers to send us un-compressed data.",
        )

    def request(self, flow):
        if ctx.options.anticomp:
            flow.request.anticomp()
