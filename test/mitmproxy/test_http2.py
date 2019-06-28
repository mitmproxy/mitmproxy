import pytest

from mitmproxy import http2
from mitmproxy import flowfilter
from mitmproxy.test import tflow


class TestHTTP2Flow:

    def test_copy(self):
        f = tflow.thttp2flow()
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert f is not f2

        assert f.messages is not f2.messages

        for m in f.messages:
            assert m.get_state()
            m2 = m.copy()
            assert not m == m2
            assert m is not m2

            a = m.get_state()
            b = m2.get_state()
            assert a == b

        m = http2.HTTP2Frame(False, f)
        m.set_state(f.messages[0].get_state())
        assert m.timestamp == f.messages[0].timestamp

        f = tflow.thttp2flow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.thttp2flow()
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b nonexistent", f)

        f = tflow.thttp2flow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.thttp2flow()
        assert 'HTTP2Flow' in repr(f)
        assert '->' in repr(f.messages[0])
        for frame in f.messages:
            assert frame.frame_type in repr(frame)
