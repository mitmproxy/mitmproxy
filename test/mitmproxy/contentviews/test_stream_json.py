from mitmproxy.contentviews import stream_json
from . import full_eval


def test_pretty_stream_json():
    assert stream_json.decompress_stream_json(b'x\xda\xabVJ\xcdLQ\xb2\xd2541\xab\x05\x00\x17}\x03q')
    assert not stream_json.decompress_stream_json(b"moo")
    assert not stream_json.decompress_stream_json(b'x\x9c\xabVJ\xcdLQ\xb2\xd2541\x03\x00\x14\x0c\x02\xf4')


def test_view_json():
    v = full_eval(stream_json.ViewStreamJSON())
    assert v(b'x\xda\xabVJ\xcdLQ\xb2\xd2541\xab\x05\x00\x17}\x03q')
    assert not v(b"{")
    assert not v(b'x\x9c\xabVJ\xcdLQ\xb2\xd2541\x03\x00\x14\x0c\x02\xf4')
