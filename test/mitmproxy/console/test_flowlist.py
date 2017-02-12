import mitmproxy.tools.console.flowlist as flowlist
from mitmproxy.test import tutils
from mitmproxy.test import tflow
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options
from mitmproxy.tools.console import common
from .. import mastertest
import pytest
from unittest import mock

class ScriptError(Exception):
    pass

def mock_add_log(message):
    raise ScriptError(message)


class TestFlowlist(mastertest.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 1
        o = options.Options(**opts)
        return console.master.ConsoleMaster(o, proxy.DummyServer())
    
    @mock.patch('mitmproxy.tools.console.signals.status_message.send', side_effect=mock_add_log)
    def test_new_request(self,test_func):
        m=self.mkmaster()
        x = flowlist.FlowListBox(m)
        with pytest.raises(ScriptError) as e:
            x.new_request("http://example.com:3e24","GET")
        assert "Invalid URL" in str(e)
        
        