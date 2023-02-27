import logging
import shutil
import subprocess
import tempfile

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy.log import ALERT


def get_chrome_executable() -> str | None:
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


def get_chrome_flatpak() -> str | None:
    if shutil.which("flatpak"):
        for browser in (
            "com.google.Chrome",
            "org.chromium.Chromium",
            "com.github.Eloston.UngoogledChromium",
            "com.google.ChromeDev",
        ):
            if (
                subprocess.run(
                    ["flatpak", "info", browser],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                == 0
            ):
                return browser

    return None


def get_browser_cmd() -> list[str] | None:
    if browser := get_chrome_executable():
        return [browser]
    elif browser := get_chrome_flatpak():
        return ["flatpak", "run", "-p", browser]

    return None


class Browser:
    browser: list[subprocess.Popen] = []
    tdir: list[tempfile.TemporaryDirectory] = []

    @command.command("browser.start")
    def start(self) -> None:
        """
        Start an isolated instance of Chrome that points to the currently
        running proxy.
        """
        if len(self.browser) > 0:
            logging.log(ALERT, "Starting additional browser")

        cmd = get_browser_cmd()
        if not cmd:
            logging.log(
                ALERT, "Your platform is not supported yet - please submit a patch."
            )
            return

        tdir = tempfile.TemporaryDirectory()
        self.tdir.append(tdir)
        self.browser.append(
            subprocess.Popen(
                [
                    *cmd,
                    "--user-data-dir=%s" % str(tdir.name),
                    "--proxy-server={}:{}".format(
                        ctx.options.listen_host or "127.0.0.1",
                        ctx.options.listen_port or "8080",
                    ),
                    "--disable-fre",
                    "--no-default-browser-check",
                    "--no-first-run",
                    "--disable-extensions",
                    "about:blank",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )

    def done(self):
        for browser in self.browser:
            browser.kill()
        for tdir in self.tdir:
            tdir.cleanup()
        self.browser = []
        self.tdir = []
