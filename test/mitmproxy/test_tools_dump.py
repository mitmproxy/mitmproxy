import os

from mitmproxy.tools import dump
from mitmproxy import proxy
from mitmproxy.test import tutils
from mitmproxy import log
from mitmproxy import controller
from . import mastertest


class TestDumpMaster(mastertest.MasterTest):
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
            tutils.raises(
                dump.DumpError,
                self.mkmaster, None, rfile="/nonexistent"
            )
            tutils.raises(
                dump.DumpError,
                self.mkmaster, None, rfile="test_dump.py"
            )

    def test_has_error(self):
        m = self.mkmaster(None)
        ent = log.LogEntry("foo", "error")
        ent.reply = controller.DummyReply()
        m.log(ent)
        assert m.has_errored
