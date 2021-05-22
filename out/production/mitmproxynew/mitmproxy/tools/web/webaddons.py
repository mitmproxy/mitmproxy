import webbrowser

from mitmproxy import ctx
from typing import Sequence


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
        loader.add_option(
            "web_columns", Sequence[str], ["tls", "icon", "path", "method", "status", "size", "time"],
            "Columns to show in the flow list"
        )

    def running(self):
        if hasattr(ctx.options, "web_open_browser") and ctx.options.web_open_browser:
            web_url = f"http://{ctx.options.web_host}:{ctx.options.web_port}/"
            success = open_browser(web_url)
            if not success:
                ctx.log.info(
                    f"No web browser found. Please open a browser and point it to {web_url}",
                )


def open_browser(url: str) -> bool:
    """
    Open a URL in a browser window.
    In contrast to webbrowser.open, we limit the list of suitable browsers.
    This gracefully degrades to a no-op on headless servers, where webbrowser.open
    would otherwise open lynx.

    Returns:
        True, if a browser has been opened
        False, if no suitable browser has been found.
    """
    browsers = (
        "windows-default", "macosx",
        "wslview %s",
        "x-www-browser %s", "gnome-open %s", "xdg-open",
        "google-chrome", "chrome", "chromium", "chromium-browser",
        "firefox", "opera", "safari",
    )
    for browser in browsers:
        try:
            b = webbrowser.get(browser)
        except webbrowser.Error:
            pass
        else:
            if b.open(url):
                return True
    return False
