import pytest
from mitmproxy.coretypes import bidi


def test_bidi():
    b = bidi.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    with pytest.raises(AttributeError):
        getattr(b, "c")
    with pytest.raises(ValueError):
        bidi.BiDi(one=1, two=1)
