from mitmproxy.contentviews import octet_stream_json
from . import full_eval


def test_octet_stream_json():
    assert octet_stream_json.decompress_octet_stream_json(b'x\xda\xabVJ\xcdLQ\xb2\xd2541\xab\x05\x00\x17}\x03q')
    assert not octet_stream_json.decompress_octet_stream_json(b"moo")
    assert not octet_stream_json.decompress_octet_stream_json(b'x\x9c\xabVJ\xcdLQ\xb2\xd2541\x03\x00\x14\x0c\x02\xf4')


def test_view_json():
    v = full_eval(octet_stream_json.ViewOctetStreamJSON())
    assert v(b'x\xda\xabVJ\xcdLQ\xb2\xd2541\xab\x05\x00\x17}\x03q')
    assert not v(b"{")
    assert not v(b'x\x9c\xabVJ\xcdLQ\xb2\xd2541\x03\x00\x14\x0c\x02\xf4')
