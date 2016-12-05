from mitmproxy.test import tflow
import mitmproxy.test.tutils
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options
from mitmproxy.tools.console import common

from .. import mastertest


def test_format_keyvals():
    assert common.format_keyvals(
        [
            ("aa", "bb"),
            None,
            ("cc", "dd"),
            (None, "dd"),
            (None, "dd"),
        ]
    )


def test_options():
    assert options.Options(replay_kill_extra=True)


class TestMaster(mastertest.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 0
        o = options.Options(**opts)
        return console.master.ConsoleMaster(o, proxy.DummyServer())

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            self.dummy_cycle(m, 1, b"")
            assert len(m.view) == i

    def test_intercept(self):
        """regression test for https://github.com/mitmproxy/mitmproxy/issues/1605"""
        m = self.mkmaster(intercept="~b bar")
        f = tflow.tflow(req=mitmproxy.test.tutils.treq(content=b"foo"))
        m.request(f)
        assert not m.view[0].intercepted
        f = tflow.tflow(req=mitmproxy.test.tutils.treq(content=b"bar"))
        m.request(f)
        assert m.view[1].intercepted
        f = tflow.tflow(resp=mitmproxy.test.tutils.tresp(content=b"bar"))
        m.request(f)
        assert m.view[2].intercepted
