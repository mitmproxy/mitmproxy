from mitmproxy import ctx


class AntiComp:
    def request(self, flow):
        if ctx.options.anticomp:
            flow.request.anticomp()
