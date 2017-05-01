import mitmproxy.tools.console.help as help

from ....conftest import skip_appveyor


@skip_appveyor
class TestHelp:

    def test_helptext(self):
        h = help.HelpView(None)
        assert h.helptext()
