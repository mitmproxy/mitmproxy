import libpry
from libpathod import utils


class uparse_anchor_spec(libpry.AutoTree):
    def test_simple(self):
        assert utils.parse_anchor_spec("foo=200", {}) == ("foo", "200")
        libpry.raises(utils.AnchorError, utils.parse_anchor_spec, "*=200", {})
        libpry.raises(utils.AnchorError, utils.parse_anchor_spec, "foo=bar", {})


tests = [
    uparse_anchor_spec()
]
