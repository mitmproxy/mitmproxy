import pytest
from unittest import mock

from mitmproxy import proxy
from mitmproxy import log
from mitmproxy import controller
from mitmproxy import options
from mitmproxy.tools import dump

from .. import tservers


class TestDumpMaster(tservers.MasterTest):
    def mkmaster(self, flt, **opts):
        o = options.Options(view_filter=flt, verbosity=-1, flow_detail=0, **opts)
        m = dump.DumpMaster(o, proxy.DummyServer(), with_termlog=False, with_dumper=False)
        return m

    def test_has_error(self):
        m = self.mkmaster(None)
        ent = log.LogEntry("foo", "error")
        ent.reply = controller.DummyReply()
        m.addons.trigger("log", ent)
        assert m.errorcheck.has_errored

    @pytest.mark.parametrize("termlog", [False, True])
    def test_addons_termlog(self, termlog):
        with mock.patch('sys.stdout'):
            o = options.Options()
            m = dump.DumpMaster(o, proxy.DummyServer(), with_termlog=termlog)
            assert (m.addons.get('termlog') is not None) == termlog

    @pytest.mark.parametrize("dumper", [False, True])
    def test_addons_dumper(self, dumper):
        with mock.patch('sys.stdout'):
            o = options.Options()
            m = dump.DumpMaster(o, proxy.DummyServer(), with_dumper=dumper)
            assert (m.addons.get('dumper') is not None) == dumper
