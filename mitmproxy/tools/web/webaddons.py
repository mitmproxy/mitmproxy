import typing

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
            "web_iface", str, "127.0.0.1",
            "Web UI interface."
        )
        loader.add_option(
            "wsingleuser", typing.Optional[str], None,
            "Web UI authentication username."
        )
        loader.add_option(
            "whtpasswd", typing.Optional[str], None,
            "Web UI authentication password."
        )
