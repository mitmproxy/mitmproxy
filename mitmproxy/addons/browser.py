import logging
import shutil
import subprocess
import tempfile
from typing import List

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy.log import ALERT


def find_executable_cmd(*search_paths) -> List[str] | None:
    for browser in search_paths:
        if shutil.which(browser):
            return [browser]

    return None


def find_flatpak_cmd(*search_paths) -> List[str] | None:
    if shutil.which("flatpak"):
        for browser in search_paths:
            if (
                subprocess.run(
                    ["flatpak", "info", browser],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                == 0
            ):
                return ["flatpak", "run", "-p", browser]

    return None


class Browser:
    browser: list[subprocess.Popen] = []
    tdir: list[tempfile.TemporaryDirectory] = []

    @command.command("browser.start")
    def start(self, browser: str = "chrome") -> None:
        if len(self.browser) > 0:
            logging.log(ALERT, "Starting additional browser")

        if browser in ("chrome", "chromium"):
            self.launch_chrome()
        elif browser == "firefox":
            self.launch_firefox()

    def launch_chrome(self):
        """
        Start an isolated instance of Chrome that points to the currently
        running proxy.
        """
        cmd = find_executable_cmd(
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
        ) or find_flatpak_cmd(
            "com.google.Chrome",
            "org.chromium.Chromium",
            "com.github.Eloston.UngoogledChromium",
            "com.google.ChromeDev",
        )

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

    def launch_firefox(self) -> None:
        """
        Start an isolated instance of Firefox that points to the currently
        running proxy.
        """
        cmd = find_executable_cmd(
            "firefox",
            "mozilla-firefox",
            "mozilla",
        ) or find_flatpak_cmd(
            "org.mozilla.firefox"
        )

        if not cmd:
            logging.log(
                ALERT, "Your platform is not supported yet - please submit a patch."
            )
            return

        def generate_user_prefs():
            host = ctx.options.listen_host or "127.0.0.1"
            port = ctx.options.listen_port or "8080"
            prefs = [
                f'user_pref("datareporting.policy.firstRunURL", "");',
                'user_pref("network.proxy.type", 1);',
                'user_pref("network.proxy.share_proxy_settings", true);',
            ]
            for service in ("http", "ssl", "socks", "ftp"):
                prefs += [
                    f'user_pref("network.proxy.{service}", "{host}");',
                    f'user_pref("network.proxy.{service}_port", {port});'
                ]
            return prefs

        tdir = tempfile.TemporaryDirectory()

        # Configure proxy via prefs.js
        with open(tdir.name + "/prefs.js", "w") as file:
            file.writelines(generate_user_prefs())

        self.tdir.append(tdir)
        self.browser.append(
            subprocess.Popen(
                [
                    *cmd,
                    "--profile",
                    str(tdir.name),
                    "--safe-mode",
                    "--new-window",
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
