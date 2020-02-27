import shutil
import subprocess
import tempfile
import typing
import webbrowser

from mitmproxy import command
from mitmproxy import ctx


def get_chrome_executable() -> typing.Optional[str]:
    for browser in (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            # https://stackoverflow.com/questions/40674914/google-chrome-path-in-windows-10
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Application\chrome.exe",
            # Linux binary names from Python's webbrowser module.
            "google-chrome",
            "google-chrome-stable",
            "chrome",
            "chromium",
            "chromium-browser",
            "google-chrome-unstable",
    ):
        if shutil.which(browser):
            return browser
    return None


class Browser:
    browser = None
    tdir = None

    @command.command("browser.start")
    def start(self) -> None:
        """
            Start an isolated instance of Chrome that points to the currently
            running proxy.
        """
        if self.browser:
            if self.browser.poll() is None:
                ctx.log.alert("Browser already running")
                return
            else:
                self.done()

        cmd = get_chrome_executable()
        if not cmd:
            ctx.log.alert("Your platform is not supported yet - please submit a patch.")
            return

        self.tdir = tempfile.TemporaryDirectory()
        self.browser = subprocess.Popen(
            [
                cmd,
                "--user-data-dir=%s" % str(self.tdir.name),
                "--proxy-server=%s:%s" % (
                    ctx.options.listen_host or "127.0.0.1",
                    ctx.options.listen_port
                ),
                "--disable-fre",
                "--no-default-browser-check",
                "--no-first-run",
                "--disable-extensions",

                "about:blank",
            ],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )

    def running(self):
        if hasattr(ctx.options, "web_open_browser") and ctx.options.web_open_browser:
            web_url = "http://{}:{}/".format(ctx.options.web_iface, ctx.options.web_port)
            success = open_browser(web_url)
            if not success:
                ctx.log.info(
                    "No web browser found. Please open a browser and point it to {}".format(web_url),
                )

    def done(self):
        if self.browser:
            self.browser.kill()
            self.tdir.cleanup()
        self.browser = None
        self.tdir = None


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
        "google-chrome", "chrome", "chromium", "chromium-browser",
        "firefox", "opera", "safari",
    )
    for browser in browsers:
        try:
            b = webbrowser.get(browser)
        except webbrowser.Error:
            pass
        else:
            b.open(url)
            return True
    return False
