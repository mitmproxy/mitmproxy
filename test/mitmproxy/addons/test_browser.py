from unittest import mock

from mitmproxy.addons import browser
from mitmproxy.test import taddons


def test_browser(caplog):
    caplog.set_level("INFO")
    with (
        mock.patch("subprocess.Popen") as po,
        mock.patch("shutil.which") as which,
        taddons.context(),
    ):
        which.return_value = "chrome"
        b = browser.Browser()
        b.start()
        assert po.called

        b.start()
        assert "Starting additional browser" in caplog.text
        assert len(b.browser) == 2
        b.done()
        assert not b.browser


async def test_no_browser(caplog):
    caplog.set_level("INFO")
    with mock.patch("shutil.which") as which:
        which.return_value = False

        b = browser.Browser()
        b.start()
        assert "platform is not supported" in caplog.text


async def test_get_browser_cmd_executable():
    with mock.patch("shutil.which") as which:
        which.side_effect = lambda cmd: cmd == "chrome"
        assert browser.get_browser_cmd() == ["chrome"]


async def test_get_browser_cmd_no_executable():
    with mock.patch("shutil.which") as which:
        which.return_value = False
        assert browser.get_browser_cmd() is None


async def test_get_browser_cmd_flatpak():
    def subprocess_run_mock(cmd, **kwargs):
        returncode = 0 if cmd == ["flatpak", "info", "com.google.Chrome"] else 1
        return mock.Mock(returncode=returncode)

    with (
        mock.patch("shutil.which") as which,
        mock.patch("subprocess.run") as subprocess_run,
    ):
        which.side_effect = lambda cmd: cmd == "flatpak"
        subprocess_run.side_effect = subprocess_run_mock
        assert browser.get_browser_cmd() == [
            "flatpak",
            "run",
            "-p",
            "com.google.Chrome",
        ]


async def test_get_browser_cmd_no_flatpak():
    with (
        mock.patch("shutil.which") as which,
        mock.patch("subprocess.run") as subprocess_run,
    ):
        which.side_effect = lambda cmd: cmd == "flatpak"
        subprocess_run.return_value = mock.Mock(returncode=1)
        assert browser.get_browser_cmd() is None
