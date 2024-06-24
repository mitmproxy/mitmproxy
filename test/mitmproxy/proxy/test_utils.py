import pytest

from mitmproxy.proxy.utils import expect
from mitmproxy.proxy.utils import ReceiveBuffer


def test_expect():
    class Foo:
        @expect(str, int)
        def foo(self, x):
            return "".join(reversed(x))

        @expect(str)
        def bar(self, x):
            yield "".join(reversed(x))

    f = Foo()

    assert f.foo("foo") == "oof"
    assert list(f.bar("bar")) == ["rab"]
    with pytest.raises(AssertionError, match=r"Expected str\|int, got None."):
        f.foo(None)


def test_receive_buffer():
    buf = ReceiveBuffer()
    assert len(buf) == 0
    assert bytes(buf) == b""
    assert not buf

    buf += b"foo"
    assert len(buf) == 3
    assert bytes(buf) == b"foo"
    assert buf

    buf += b"bar"
    assert len(buf) == 6
    assert bytes(buf) == b"foobar"
    assert buf

    buf.clear()
    assert len(buf) == 0
    assert bytes(buf) == b""
    assert not buf
