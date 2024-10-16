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

        b.start("unsupported-browser")
        assert "Invalid browser name." in caplog.text
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


async def test_find_executable_cmd():
    with mock.patch("shutil.which") as which:
        which.side_effect = lambda cmd: cmd == "chrome"
        assert browser.find_executable_cmd("chrome") == ["chrome"]


async def test_find_executable_cmd_no_executable():
    with mock.patch("shutil.which") as which:
        which.return_value = False
        assert browser.find_executable_cmd("chrome") is None


async def test_find_flatpak_cmd():
    def subprocess_run_mock(cmd, **kwargs):
        returncode = 0 if cmd == ["flatpak", "info", "com.google.Chrome"] else 1
        return mock.Mock(returncode=returncode)

    with (
        mock.patch("shutil.which") as which,
        mock.patch("subprocess.run") as subprocess_run,
    ):
        which.side_effect = lambda cmd: cmd == "flatpak"
        subprocess_run.side_effect = subprocess_run_mock
        assert browser.find_flatpak_cmd("com.google.Chrome") == [
            "flatpak",
            "run",
            "-p",
            "com.google.Chrome",
        ]


async def test_find_flatpak_cmd_no_flatpak():
    with (
        mock.patch("shutil.which") as which,
        mock.patch("subprocess.run") as subprocess_run,
    ):
        which.side_effect = lambda cmd: cmd == "flatpak"
        subprocess_run.return_value = mock.Mock(returncode=1)
        assert browser.find_flatpak_cmd("com.google.Chrome") is None


async def test_browser_start_firefox():
    with (
        mock.patch("shutil.which") as which,
        mock.patch("subprocess.Popen") as po,
        taddons.context(),
    ):
        which.return_value = "firefox"
        browser.Browser().start("firefox")
        assert po.called


async def test_browser_start_firefox_not_found(caplog):
    caplog.set_level("INFO")
    with mock.patch("shutil.which") as which:
        which.return_value = False
        browser.Browser().start("firefox")
        assert "platform is not supported" in caplog.text
