from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options
from mitmproxy.tools.console import common
from ... import tservers
import urwid


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


class TestMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 1
        o = options.Options(**opts)
        m = console.master.ConsoleMaster(o, proxy.DummyServer())
        m.addons.configure_all(o, o.keys())
        return m

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            try:
                self.dummy_cycle(m, 1, b"")
            except urwid.ExitMainLoop:
                pass
            assert len(m.view) == i

    def test_run_script_once(self):
        m = self.mkmaster()
        f = tflow.tflow(resp=True)
        m.run_script_once("nonexistent", [f])
        assert any("Input error" in str(l) for l in m.logbuffer)

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
