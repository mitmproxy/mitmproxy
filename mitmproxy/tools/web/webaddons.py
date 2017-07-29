class WebOptions:
    def load(self, loader):
        loader.add_option(
            "web_open_browser", bool, True,
            "Start a browser."
        )
        loader.add_option(
            "web_debug", bool, False,
            "Mitmweb debugging."
        )
        loader.add_option(
            "web_port", int, 8081,
            "Mitmweb port."
        )
        loader.add_option(
            "web_iface", str, "127.0.0.1",
            "Mitmweb interface."
        )
