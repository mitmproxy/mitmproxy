import sys
import libpry
import libmproxy.console.help as help
from libmproxy import utils, flow, encoding

class DummyMaster:
    def make_view(self):
        pass


class uHelp(libpry.AutoTree):
    def test_helptext(self):
        h = help.HelpView(None, "foo", None)
        assert h.helptext()

    def test_keypress(self):
        h = help.HelpView(DummyMaster(), "foo", [1, 2, 3])
        assert not h.keypress((0, 0), "q")
        assert not h.keypress((0, 0), "?")
        assert h.keypress((0, 0), "o") == "o"


tests = [
    uHelp()
]
