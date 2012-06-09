from libpathod import utils
import tutils


def test_parse_anchor_spec():
    assert utils.parse_anchor_spec("foo=200", {}) == ("foo", "200")
    tutils.raises(utils.AnchorError, utils.parse_anchor_spec, "foobar", {})
    tutils.raises(utils.AnchorError, utils.parse_anchor_spec, "*=200", {})
    tutils.raises(utils.AnchorError, utils.parse_anchor_spec, "foo=bar", {})


def test_data_path():
    tutils.raises(ValueError, utils.data.path, "nonexistent")
