import mitmproxy_rs
from mitmproxy.tools.console import palettes


class TestPalette:
    def test_helptext(self):
        for i in palettes.palettes.values():
            assert i.palette(False)
        for i in palettes.palettes.values():
            assert i.palette(True)

    def test_has_tags(self):
        missing = set(mitmproxy_rs.syntax_highlight.tags()) - set(
            palettes.Palette._fields
        )
        assert not missing, f"Missing styles for tags: {missing}"
