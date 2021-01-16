import pytest

from mitmproxy.proxy.utils import expect


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
