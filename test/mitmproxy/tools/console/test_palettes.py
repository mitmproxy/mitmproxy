import mitmproxy.tools.console.palettes as palettes

from ...conftest import skip_appveyor


@skip_appveyor
class TestPalette:

    def test_helptext(self):
        for i in palettes.palettes.values():
            assert i.palette(False)
        for i in palettes.palettes.values():
            assert i.palette(True)
