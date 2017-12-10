import subprocess
import sys
import tempfile

from mitmproxy import command
from mitmproxy import ctx

platformPaths = {
    "linux": "google-chrome",
    "win32": "chrome.exe",
    "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
}


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

        cmd = platformPaths.get(sys.platform)
        if not cmd:  # pragma: no cover
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