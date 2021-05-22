import pytest

from mitmproxy import tcp
from mitmproxy import flowfilter
from mitmproxy.test import tflow


class TestTCPFlow:

    def test_copy(self):
        f = tflow.ttcpflow()
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

        m = tcp.TCPMessage(False, 'foo')
        m.set_state(f.messages[0].get_state())
        assert m.timestamp == f.messages[0].timestamp

        f = tflow.ttcpflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.ttcpflow()
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b nonexistent", f)

        f = tflow.ttcpflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.ttcpflow()
        assert 'TCPFlow' in repr(f)
        assert '-> ' in repr(f.messages[0])
