from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options
from mitmproxy.tools.console import common
from ... import tservers


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
        return console.master.ConsoleMaster(o, proxy.DummyServer())

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            self.dummy_cycle(m, 1, b"")
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
        m.request(f)
        assert not m.view[0].intercepted
        f = tflow.tflow(req=tutils.treq(content=b"bar"))
        m.request(f)
        assert m.view[1].intercepted
        f = tflow.tflow(resp=tutils.tresp(content=b"bar"))
        m.request(f)
        assert m.view[2].intercepted

    def test_replace_view_state(self):
        w1 = console.window.Window(self, None, None, None, None)
        w2 = console.window.Window(self, None, None, None, None)
        m = self.mkmaster()
        m.view_stack.append(w1)
        m.view_stack.append(w2)

        assert len(m.view_stack) == 2
        console.signals.replace_view_state.send(self)
        assert len(m.view_stack) == 1
