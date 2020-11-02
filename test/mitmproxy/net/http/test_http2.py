import pytest
import codecs
from io import BytesIO

import hyperframe

from mitmproxy import exceptions
from mitmproxy.net.http import http2


def test_read_frame():
    raw = codecs.decode('000006000101234567666f6f626172', 'hex_codec')
    bio = BytesIO(raw)
    bio.safe_read = bio.read

    frame, consumed_bytes = http2.read_frame(bio)
    assert isinstance(frame, hyperframe.frame.DataFrame)
    assert frame.stream_id == 19088743
    assert 'END_STREAM' in frame.flags
    assert len(frame.flags) == 1
    assert frame.data == b'foobar'
    assert consumed_bytes == raw

    bio = BytesIO(raw)
    bio.safe_read = bio.read
    frame, consumed_bytes = http2.read_frame(bio, False)
    assert frame is None
    assert consumed_bytes == raw


def test_read_frame_failed():
    raw = codecs.decode('485454000000000000', 'hex_codec')
    bio = BytesIO(raw)
    bio.safe_read = bio.read

    with pytest.raises(exceptions.HttpException):
        _ = http2.read_frame(bio, False)
