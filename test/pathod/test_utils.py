from pathod import utils
import tutils


def test_membool():
    m = utils.MemBool()
    assert not m.v
    assert m(1)
    assert m.v == 1
    assert m(2)
    assert m.v == 2


def test_parse_anchor_spec():
    assert utils.parse_anchor_spec("foo=200") == ("foo", "200")
    assert utils.parse_anchor_spec("foo") is None


def test_data_path():
    tutils.raises(ValueError, utils.data.path, "nonexistent")
