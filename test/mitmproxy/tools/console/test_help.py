import mitmproxy.tools.console.help as help

from ....conftest import skip_appveyor


@skip_appveyor
class TestHelp:

    def test_helptext(self):
        h = help.HelpView(None)
        assert h.helptext()

    def test_keypress(self):
        h = help.HelpView([1, 2, 3])
        assert not h.keypress((0, 0), "q")
        assert not h.keypress((0, 0), "?")
        assert h.keypress((0, 0), "o") == "o"
