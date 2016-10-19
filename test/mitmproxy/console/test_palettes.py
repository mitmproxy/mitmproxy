import mitmproxy.tools.console.palettes as palettes
from .. import tutils


@tutils.skip_appveyor
class TestPalette:

    def test_helptext(self):
        for i in palettes.palettes.values():
            assert i.palette(False)
        for i in palettes.palettes.values():
            assert i.palette(True)
