import webbrowser

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
            success = open_browser(web_url)
            if not success:
                ctx.log.info(
                    "No web browser found. Please open a browser and point it to {}".format(web_url),
                )


def open_browser(url: str) -> bool:
    """
    Open a URL in a browser window.
    In contrast to webbrowser.open, we only open a browser if it will run in
    the background.
    This gracefully degrades to a no-op on headless servers, where webbrowser.open
    would otherwise open lynx.

    Returns:
        True, if a browser has been opened
        False, if no suitable browser has been found.
    """
    try:
        b = webbrowser.get()
    except webbrowser.Error:
        return False

    browsers = tuple(getattr(webbrowser, name, type(None)) for name in [
        'WindowsDefault', 'MacOSX', 'MacOSXOSAScript',
        'BackgroundBrowser', 'Konqueror', 'Grail',
    ])
    if isinstance(b, browsers) or (isinstance(b, webbrowser.UnixBrowser) and b.background):
        return b.open(url)
    return False
