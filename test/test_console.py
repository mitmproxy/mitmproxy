import os
import sys
import mock
import gc
from os.path import normpath
import mock_urwid
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
        assert f in c.flows
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
        f = tutils.tflow()
        return state.add_flow(f)

    def _add_response(self, state):
        f = self._add_request(state)
        f.response = tutils.tresp()
        state.update_flow(f)

    def test_add_response(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        f.response = tutils.tresp()
        c.focus = None
        c.update_flow(f)

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
    assert console.Options(kill=True)
