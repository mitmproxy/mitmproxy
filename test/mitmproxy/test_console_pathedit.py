import os
from os.path import normpath
from mitmproxy.console import pathedit

from . import tutils


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
