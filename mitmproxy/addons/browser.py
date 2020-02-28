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

    def done(self):
        if self.browser:
            self.browser.kill()
            self.tdir.cleanup()
        self.browser = None
        self.tdir = None