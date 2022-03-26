import pytest

from mitmproxy import dns
from mitmproxy import flowfilter
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestMessage:

    def test_packing(self):
        def assert_eq(m: dns.Message, b: bytes) -> None:
            m_b = dns.Message.unpack(b)
            m_b.timestamp = m.timestamp
            assert m_b == m
            assert m_b.packed == m.packed

        assert_eq(tutils.tdnsreq(), b'\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01')
        assert_eq(tutils.tdnsresp(), (
            b'\x00\x2a\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01' +
            b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x08\x08\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x04\x04'
        ))

    def test_copy(self):
        msg = tutils.tdnsresp()
        assert dns.Message.from_state(msg.get_state()) == msg
        copy = msg.copy()
        assert copy is not msg
        assert copy != msg
        copy.id = msg.id
        assert copy == msg
        assert copy.questions is not msg.questions
        assert copy.questions == msg.questions
        assert copy.answers is not msg.answers
        assert copy.answers == msg.answers
        assert copy.authorities is not msg.authorities
        assert copy.authorities == msg.authorities
        assert copy.additionals is not msg.additionals
        assert copy.additionals == msg.additionals


class TestDNSFlow:

    def test_copy(self):
        f = tflow.tdnsflow(resp=True)
        assert repr(f)
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert f is not f2

        assert f.request.get_state() == f2.request.get_state()
        assert f.request is not f2.request
        assert f.request == f2.request
        assert f.response is not f2.response
        assert f.response.get_state() == f2.response.get_state()
        assert f.response == f2.response

        f = tflow.tdnsflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.request is not f2.request
        assert f.request == f2.request
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.tdnsflow(resp=True)
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert flowfilter.match("~b dns.google", f)
        assert flowfilter.match("~b 8.8.8.8", f)

        assert flowfilter.match("~bq dns.google", f)
        assert not flowfilter.match("~bq 8.8.8.8", f)

        assert flowfilter.match("~bs dns.google", f)
        assert flowfilter.match("~bs 8.8.4.4", f)

        assert flowfilter.match("~dns", f)
        assert not flowfilter.match("~dns", tflow.ttcpflow())
        assert not flowfilter.match("~dns", tflow.tflow())

        f = tflow.tdnsflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.tdnsflow()
        assert 'DNSFlow' in repr(f)
