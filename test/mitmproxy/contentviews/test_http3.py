import pytest

from . import full_eval
from mitmproxy.contentviews import http3
from mitmproxy.tcp import TCPMessage
from mitmproxy.test import tflow


@pytest.mark.parametrize(
    "data",
    [
        # HEADERS
        b"\x01\x1d\x00\x00\xd1\xc1\xd7P\x8a\x08\x9d\\\x0b\x81p\xdcx\x0f\x03_P\x88%\xb6P\xc3\xab\xbc\xda\xe0\xdd",
        # broken HEADERS
        b"\x01\x1d\x00\x00\xd1\xc1\xd7P\x8a\x08\x9d\\\x0b\x81p\xdcx\x0f\x03_P\x88%\xb6P\xc3\xab\xff\xff\xff\xff",
        # headers + data
        (
            b"\x01@I\x00\x00\xdb_'\x93I|\xa5\x89\xd3M\x1fj\x12q\xd8\x82\xa6\x0bP\xb0\xd0C\x1b_M\x90\xd0bXt\x1eT\xad\x8f~\xfdp"
            b"\xeb\xc8\xc0\x97\x07V\x96\xd0z\xbe\x94\x08\x94\xdcZ\xd4\x10\x04%\x02\xe5\xc6\xde\xb8\x17\x14\xc5\xa3\x7fT\x03315"
            b'\x00A;<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN""http://www.w3.org/TR/html4/strict.dtd">\r\n<HTML><HEAD><'
            b'TITLE>Not Found</TITLE>\r\n<META HTTP-EQUIV="Content-Type" Content="text/html; charset=us-ascii"></HEAD>\r\n<BOD'
            b"Y><h2>Not Found</h2>\r\n<hr><p>HTTP Error 404. The requested resource is not found.</p>\r\n</BODY></HTML>\r\n"
        ),
        b"",
    ],
)
def test_view_http3(data):
    v = full_eval(http3.ViewHttp3())
    t = tflow.ttcpflow(messages=[TCPMessage(from_client=len(data) > 16, content=data)])
    t.metadata["quic_is_unidirectional"] = False
    assert v(b"", flow=t, tcp_message=t.messages[0])


@pytest.mark.parametrize(
    "data",
    [
        # SETTINGS
        b"\x00\x04\r\x06\xff\xff\xff\xff\xff\xff\xff\xff\x01\x00\x07\x00",
        # unknown setting
        b"\x00\x04\r\x3f\xff\xff\xff\xff\xff\xff\xff\xff\x01\x00\x07\x00",
        # out of bounds
        b"\x00\x04\r\x06\xff\xff\xff\xff\xff\xff\xff\xff\x01\x00\x42\x00",
        # incomplete
        b"\x00\x04\r\x06\xff\xff\xff",
        # QPACK encoder stream
        b"\x02",
    ],
)
def test_view_http3_unidirectional(data):
    v = full_eval(http3.ViewHttp3())
    t = tflow.ttcpflow(messages=[TCPMessage(from_client=len(data) > 16, content=data)])
    t.metadata["quic_is_unidirectional"] = True
    assert v(b"", flow=t, tcp_message=t.messages[0])


def test_render_priority():
    v = http3.ViewHttp3()
    assert not v.render_priority(b"random stuff")
