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

    def test_unstyled_content_background(self):
        opaque = next(
            entry for entry in palettes.SolarizedDark().palette(False) if not entry[0]
        )
        transparent = next(
            entry for entry in palettes.SolarizedDark().palette(True) if not entry[0]
        )

        assert opaque[2] == "black"
        assert opaque[5] == "h234"
        assert transparent[2] == "default"
        assert transparent[5] == "default"
