import pytest

from pathod import utils


def test_membool():
    m = utils.MemBool()
    assert not m.v
    assert m(1)
    assert m.v == 1
    assert m(2)
    assert m.v == 2


def test_data_path():
    with pytest.raises(ValueError):
        utils.data.path("nonexistent")
