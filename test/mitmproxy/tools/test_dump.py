from unittest import mock

import pytest

from mitmproxy import controller
from mitmproxy import log
from mitmproxy import options
from mitmproxy.tools import dump


class TestDumpMaster:
    def mkmaster(self, **opts):
        o = options.Options(**opts)
        m = dump.DumpMaster(o, with_termlog=False, with_dumper=False)
        return m

    def test_has_error(self):
        m = self.mkmaster()
        ent = log.LogEntry("foo", "error")
        ent.reply = controller.DummyReply()
        m.addons.trigger(log.AddLogHook(ent))
        assert m.errorcheck.has_errored

    @pytest.mark.parametrize("termlog", [False, True])
    def test_addons_termlog(self, termlog):
        with mock.patch('sys.stdout'):
            o = options.Options()
            m = dump.DumpMaster(o, with_termlog=termlog)
            assert (m.addons.get('termlog') is not None) == termlog

    @pytest.mark.parametrize("dumper", [False, True])
    def test_addons_dumper(self, dumper):
        with mock.patch('sys.stdout'):
            o = options.Options()
            m = dump.DumpMaster(o, with_dumper=dumper)
            assert (m.addons.get('dumper') is not None) == dumper
