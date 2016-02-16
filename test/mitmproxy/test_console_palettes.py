import os
from unittest.case import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")
import mitmproxy.console.palettes as palettes


class TestPalette:

    def test_helptext(self):
        for i in palettes.palettes.values():
            assert i.palette(False)
        for i in palettes.palettes.values():
            assert i.palette(True)
