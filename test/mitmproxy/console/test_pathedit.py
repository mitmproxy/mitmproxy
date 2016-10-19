import os
from os.path import normpath
from mitmproxy.tools.console import pathedit

from mock import patch

from .. import tutils


class TestPathCompleter:

    def test_lookup_construction(self):
        c = pathedit._PathCompleter()

        cd = tutils.test_data.path("completion")
        ca = os.path.join(cd, "a")
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        assert c.complete(ca).endswith(normpath("/completion/aab"))
        c.reset()
        ca = os.path.join(cd, "aaa")
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        c.reset()
        assert c.complete(cd).endswith(normpath("/completion/aaa"))

    def test_completion(self):
        c = pathedit._PathCompleter(True)
        c.reset()
        c.lookup = [
            ("a", "x/a"),
            ("aa", "x/aa"),
        ]
        assert c.complete("a") == "a"
        assert c.final == "x/a"
        assert c.complete("a") == "aa"
        assert c.complete("a") == "a"

        c = pathedit._PathCompleter(True)
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


class TestPathEdit:

    def test_keypress(self):

        pe = pathedit.PathEdit()

        with patch('urwid.widget.Edit.get_edit_text') as get_text, \
                patch('urwid.widget.Edit.set_edit_text') as set_text:

            cd = tutils.test_data.path("completion")
            get_text.return_value = os.path.join(cd, "a")

            # Pressing tab should set completed path
            pe.keypress((1,), "tab")
            set_text_called_with = set_text.call_args[0][0]
            assert set_text_called_with.endswith(normpath("/completion/aaa"))

            # Pressing any other key should reset
            pe.keypress((1,), "a")
            assert pe.lookup is None
