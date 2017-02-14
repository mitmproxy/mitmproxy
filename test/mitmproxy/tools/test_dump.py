import os
import pytest
from unittest import mock

from mitmproxy import proxy
from mitmproxy import log
from mitmproxy import controller
from mitmproxy.tools import dump

from mitmproxy.test import tutils
from .. import tservers


class TestDumpMaster(tservers.MasterTest):
    def mkmaster(self, flt, **options):
        o = dump.Options(filtstr=flt, verbosity=-1, flow_detail=0, **options)
        m = dump.DumpMaster(o, proxy.DummyServer(), with_termlog=False, with_dumper=False)
        return m

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            self.flowfile(p)
            self.dummy_cycle(
                self.mkmaster(None, rfile=p),
                1, b"",
            )
            with pytest.raises(dump.DumpError):
                self.mkmaster(None, rfile="/nonexistent")
            with pytest.raises(dump.DumpError):
                self.mkmaster(None, rfile="test_dump.py")

    def test_has_error(self):
        m = self.mkmaster(None)
        ent = log.LogEntry("foo", "error")
        ent.reply = controller.DummyReply()
        m.log(ent)
        assert m.has_errored

    @pytest.mark.parametrize("termlog", [False, True])
    def test_addons_termlog(self, termlog):
        with mock.patch('sys.stdout'):
            o = dump.Options()
            m = dump.DumpMaster(o, proxy.DummyServer(), with_termlog=termlog)
            assert (m.addons.get('termlog') is not None) == termlog

    @pytest.mark.parametrize("dumper", [False, True])
    def test_addons_dumper(self, dumper):
        with mock.patch('sys.stdout'):
            o = dump.Options()
            m = dump.DumpMaster(o, proxy.DummyServer(), with_dumper=dumper)
            assert (m.addons.get('dumper') is not None) == dumper
