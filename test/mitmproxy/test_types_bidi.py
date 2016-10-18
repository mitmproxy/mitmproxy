from mitmproxy.types import bidi
from mitmproxy.test import tutils


def test_bidi():
    b = bidi.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, bidi.BiDi, one=1, two=1)
