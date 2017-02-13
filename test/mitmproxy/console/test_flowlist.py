import mitmproxy.tools.console.flowlist as flowlist
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options
from .. import tservers
import pytest
from unittest import mock


class UrlError(Exception):
    pass


def mock_add_log(message):
    raise UrlError(message)


class TestFlowlist(tservers.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 1
        o = options.Options(**opts)
        return console.master.ConsoleMaster(o, proxy.DummyServer())

    @mock.patch('mitmproxy.tools.console.signals.status_message.send', side_effect = mock_add_log)
    def test_new_request(self, test_func):
        m = self.mkmaster()
        x = flowlist.FlowListBox(m)
        with pytest.raises(UrlError) as e:
            x.new_request("nonexistent url", "GET")
        assert "Invalid URL" in str(e)
