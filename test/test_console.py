import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

from libmproxy import console
from libmproxy.console import common
import tutils

class TestConsoleState:
    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
        f = self._add_request(c)
        assert f.request in c._flow_map
        assert c.get_focus() == (f, 0)

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
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
        r = tutils.treq()
        return state.add_request(r)

    def _add_response(self, state):
        f = self._add_request(state)
        r = tutils.tresp(f.request)
        state.add_response(r)

    def test_add_response(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        r = tutils.tresp(f.request)
        c.focus = None
        c.add_response(r)

    def test_focus_view(self):
        c = console.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        assert not c.set_limit("~s")
        assert len(c.view) == 3
        assert c.focus == 0

    def test_settings(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        c.add_flow_setting(f, "foo", "bar")
        assert c.get_flow_setting(f, "foo") == "bar"
        assert c.get_flow_setting(f, "oink") == None
        assert c.get_flow_setting(f, "oink", "foo") == "foo"
        assert len(c.flowsettings) == 1
        c.delete_flow(f)
        del f
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


class TestPathCompleter:
    def test_lookup_construction(self):
        c = console._PathCompleter()
        assert c.complete("/tm") == "/tmp/"
        c.reset()

        cd = tutils.test_data.path("completion")
        ca = os.path.join(cd, "a")
        assert c.complete(ca).endswith("/completion/aaa")
        assert c.complete(ca).endswith("/completion/aab")
        c.reset()
        ca = os.path.join(cd, "aaa")
        assert c.complete(ca).endswith("/completion/aaa")
        assert c.complete(ca).endswith("/completion/aaa")
        c.reset()
        assert c.complete(cd).endswith("/completion/aaa")

    def test_completion(self):
        c = console._PathCompleter(True)
        c.reset()
        c.lookup = [
            ("a", "x/a"),
            ("aa", "x/aa"),
        ]
        assert c.complete("a") == "a"
        assert c.final == "x/a"
        assert c.complete("a") == "aa"
        assert c.complete("a") == "a"

        c = console._PathCompleter(True)
        r = c.complete("l")
        assert c.final.endswith(r)

        c.reset()
        assert c.complete("/nonexistent") == "/nonexistent"
        assert c.final == "/nonexistent"
        c.reset()
        assert c.complete("~") != "~"

        c.reset()
        s = "thisisatotallynonexistantpathforsure"
        assert c.complete(s) == s
        assert c.final == s


def test_options():
    assert console.Options(kill=True)
