import native_web_app
from mitmproxy import ctx


class WebAddon:
    def load(self, loader):
        loader.add_option(
            "web_open_browser", bool, True,
            "Start a browser."
        )
        loader.add_option(
            "web_debug", bool, False,
            "Enable mitmweb debugging."
        )
        loader.add_option(
            "web_port", int, 8081,
            "Web UI port."
        )
        loader.add_option(
            "web_host", str, "127.0.0.1",
            "Web UI host."
        )

    def running(self):
        if hasattr(ctx.options, "web_open_browser") and ctx.options.web_open_browser:
            web_url = "http://{}:{}/".format(ctx.options.web_host, ctx.options.web_port)
            try:
                native_web_app.open(web_url)
            except Exception:
                ctx.log.info(
                    "No web browser found. Please open a browser and point it to {}".format(web_url),
                )
