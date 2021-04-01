from mitmproxy import ctx


class AntiCache:
    def load(self, loader):
        loader.add_option(
            "anticache", bool, False,
            """
            Strip out request headers that might cause the server to return
            304-not-modified.
            """
        )

    def request(self, flow):
        if ctx.options.anticache:
            flow.request.anticache()
