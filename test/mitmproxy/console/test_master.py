import gc

import mitmproxy.test.tutils
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy.tools.console import common

from .. import tutils, mastertest


class TestConsoleState:

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.master.ConsoleState()
        f = self._add_request(c)
        assert f in c.flows
        assert c.get_focus() == (f, 0)

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.master.ConsoleState()
        f = self._add_request(c)

        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        f2 = self._add_request(c)
        assert c.get_focus() == (f, 0)
        assert c.get_next(0) == (f2, 1)
        assert c.get_prev(1) == (f, 0)
        assert c.get_next(1) == (None, None)

        c.set_focus(0)
        assert c.get_focus() == (f, 0)
        c.set_focus(-1)
        assert c.get_focus() == (f, 0)
        c.set_focus(2)
        assert c.get_focus() == (f2, 1)

        c.delete_flow(f2)
        assert c.get_focus() == (f, 0)
        c.delete_flow(f)
        assert c.get_focus() == (None, None)

    def _add_request(self, state):
        f = tutils.tflow()
        return state.add_flow(f)

    def _add_response(self, state):
        f = self._add_request(state)
        f.response = mitmproxy.test.tutils.tresp()
        state.update_flow(f)

    def test_add_response(self):
        c = console.master.ConsoleState()
        f = self._add_request(c)
        f.response = mitmproxy.test.tutils.tresp()
        c.focus = None
        c.update_flow(f)

    def test_focus_view(self):
        c = console.master.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        assert not c.set_view_filter("~s")
        assert len(c.view) == 3
        assert c.focus == 0

    def test_settings(self):
        c = console.master.ConsoleState()
        f = self._add_request(c)
        c.add_flow_setting(f, "foo", "bar")
        assert c.get_flow_setting(f, "foo") == "bar"
        assert c.get_flow_setting(f, "oink") is None
        assert c.get_flow_setting(f, "oink", "foo") == "foo"
        assert len(c.flowsettings) == 1
        c.delete_flow(f)
        del f
        gc.collect()
        assert len(c.flowsettings) == 0


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
    assert console.master.Options(replay_kill_extra=True)


class TestMaster(mastertest.MasterTest):
    def mkmaster(self, **options):
        if "verbosity" not in options:
            options["verbosity"] = 0
        o = console.master.Options(**options)
        return console.master.ConsoleMaster(o, proxy.DummyServer())

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            self.dummy_cycle(m, 1, b"")
            assert len(m.state.flows) == i

    def test_intercept(self):
        """regression test for https://github.com/mitmproxy/mitmproxy/issues/1605"""
        m = self.mkmaster(intercept="~b bar")
        f = tutils.tflow(req=mitmproxy.test.tutils.treq(content=b"foo"))
        m.request(f)
        assert not m.state.flows[0].intercepted
        f = tutils.tflow(req=mitmproxy.test.tutils.treq(content=b"bar"))
        m.request(f)
        assert m.state.flows[1].intercepted
        f = tutils.tflow(resp=mitmproxy.test.tutils.tresp(content=b"bar"))
        m.request(f)
        assert m.state.flows[2].intercepted
