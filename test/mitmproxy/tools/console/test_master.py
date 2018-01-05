import urwid

from mitmproxy import options
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.tools import console
from ... import tservers


def test_options():
    assert options.Options(replay_kill_extra=True)


class TestMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 'warn'
        o = options.Options(**opts)
        m = console.master.ConsoleMaster(o)
        m.addons.trigger("configure", o.keys())
        return m

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            try:
                self.dummy_cycle(m, 1, b"")
            except urwid.ExitMainLoop:
                pass
            assert len(m.view) == i

    def test_intercept(self):
        """regression test for https://github.com/mitmproxy/mitmproxy/issues/1605"""
        m = self.mkmaster(intercept="~b bar")
        f = tflow.tflow(req=tutils.treq(content=b"foo"))
        m.addons.handle_lifecycle("request", f)
        assert not m.view[0].intercepted
        f = tflow.tflow(req=tutils.treq(content=b"bar"))
        m.addons.handle_lifecycle("request", f)
        assert m.view[1].intercepted
        f = tflow.tflow(resp=tutils.tresp(content=b"bar"))
        m.addons.handle_lifecycle("request", f)
        assert m.view[2].intercepted
