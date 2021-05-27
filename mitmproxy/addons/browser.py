import shutil
import subprocess
import tempfile
import typing

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
    browser: typing.List[subprocess.Popen] = []
    tdir: typing.List[tempfile.TemporaryDirectory] = []

    @command.command("browser.start")
    def start(self) -> None:
        """
            Start an isolated instance of Chrome that points to the currently
            running proxy.
        """
        if len(self.browser) > 0:
            ctx.log.alert("Starting additional browser")

        cmd = get_chrome_executable()
        if not cmd:
            ctx.log.alert("Your platform is not supported yet - please submit a patch.")
            return

        tdir = tempfile.TemporaryDirectory()
        self.tdir.append(tdir)
        self.browser.append(subprocess.Popen(
            [
                cmd,
                "--user-data-dir=%s" % str(tdir.name),
                "--proxy-server={}:{}".format(
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
        ))

    def done(self):
        for browser in self.browser:
            browser.kill()
        for tdir in self.tdir:
            tdir.cleanup()
        self.browser = []
        self.tdir = []