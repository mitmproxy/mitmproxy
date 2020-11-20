import time
from pathlib import Path
from unittest import mock

from mitmproxy.connections import ServerConnection
from mitmproxy.exceptions import HttpSyntaxException
from mitmproxy.test import tflow
from mitmproxy.test import tutils
import multiprocessing

from examples.contrib.webscanner_helper.watchdog import WatchdogAddon, logger


class TestWatchdog:

    def test_init_file(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write("")
        event = multiprocessing.Event()
        try:
            WatchdogAddon(event, Path(tmpfile))
        except RuntimeError:
            assert True
        else:
            assert False

    def test_init_dir(self, tmpdir):
        event = multiprocessing.Event()
        mydir = tmpdir.join("mydir")
        assert not Path(mydir).exists()
        WatchdogAddon(event, Path(mydir))
        assert Path(mydir).exists()

    def test_serverconnect(self, tmpdir):
        event = multiprocessing.Event()
        w = WatchdogAddon(event, Path(tmpdir), timeout=10)
        with mock.patch('mitmproxy.connections.ServerConnection.settimeout') as mock_set_timeout:
            w.serverconnect(ServerConnection("127.0.0.1"))
        mock_set_timeout.assert_called()

    def test_serverconnect_None(self, tmpdir):
        event = multiprocessing.Event()
        w = WatchdogAddon(event, Path(tmpdir))
        with mock.patch('mitmproxy.connections.ServerConnection.settimeout') as mock_set_timeout:
            w.serverconnect(ServerConnection("127.0.0.1"))
        assert not mock_set_timeout.called

    def test_trigger(self, tmpdir):
        event = multiprocessing.Event()
        w = WatchdogAddon(event, Path(tmpdir))
        f = tflow.tflow(resp=tutils.tresp())
        f.error = "Test Error"

        with mock.patch.object(logger, 'error') as mock_error:
            open_mock = mock.mock_open()
            with mock.patch("pathlib.Path.open", open_mock, create=True):
                w.error(f)
            mock_error.assert_called()
            open_mock.assert_called()

    def test_trigger_http_synatx(self, tmpdir):
        event = multiprocessing.Event()
        w = WatchdogAddon(event, Path(tmpdir))
        f = tflow.tflow(resp=tutils.tresp())
        f.error = HttpSyntaxException()
        assert isinstance(f.error, HttpSyntaxException)

        with mock.patch.object(logger, 'error') as mock_error:
            open_mock = mock.mock_open()
            with mock.patch("pathlib.Path.open", open_mock, create=True):
                w.error(f)
            assert not mock_error.called
            assert not open_mock.called

    def test_timeout(self, tmpdir):
        event = multiprocessing.Event()
        w = WatchdogAddon(event, Path(tmpdir))

        assert w.not_in_timeout(None, None)
        assert w.not_in_timeout(time.time, None)
        with mock.patch('time.time', return_value=5):
            assert not w.not_in_timeout(3, 20)
            assert w.not_in_timeout(3, 1)
