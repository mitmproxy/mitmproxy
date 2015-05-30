import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import libmproxy.console.help as help


class DummyLoop:
    def __init__(self):
        self.widget = None


class DummyMaster:
    def __init__(self):
        self.loop = DummyLoop()

    def make_view(self):
        pass


class TestHelp:
    def test_helptext(self):
        h = help.HelpView(None)
        assert h.helptext()

    def test_keypress(self):
        master = DummyMaster()
        h = help.HelpView([1, 2, 3])
        assert not h.keypress((0, 0), "q")
        assert not h.keypress((0, 0), "?")
        assert h.keypress((0, 0), "o") == "o"
