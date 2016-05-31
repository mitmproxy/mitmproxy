from pathod import utils
import tutils

import six


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


def test_escape_unprintables():
    s = bytes(range(256))
    if six.PY2:
        s = "".join([chr(i) for i in range(255)])
    e = utils.escape_unprintables(s)
    assert e.encode('ascii')
    assert "PATHOD_MARKER" not in e
