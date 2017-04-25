from mitmproxy import ctx


class AntiCache:
    def request(self, flow):
        if ctx.options.anticache:
            flow.request.anticache()
