import pytest
import codecs
from io import BytesIO
import hyperframe.frame

from mitmproxy import exceptions
from mitmproxy.net.http.http2 import read_raw_frame, parse_frame


def test_read_raw_frame():
    raw = codecs.decode('000006000101234567666f6f626172', 'hex_codec')
    bio = BytesIO(raw)
    bio.safe_read = bio.read

    header, body = read_raw_frame(bio)
    assert header
    assert body


def test_read_raw_frame_failed():
    raw = codecs.decode('485454000000000000', 'hex_codec')
    bio = BytesIO(raw)
    bio.safe_read = bio.read

    with pytest.raises(exceptions.HttpException):
        read_raw_frame(bio)


def test_parse_frame():
    f = parse_frame(
        codecs.decode('000006000101234567', 'hex_codec'),
        codecs.decode('666f6f626172', 'hex_codec')
    )
    assert isinstance(f, hyperframe.frame.Frame)


def test_parse_frame_combined():
    f = parse_frame(
        codecs.decode('000006000101234567666f6f626172', 'hex_codec'),
    )
    assert isinstance(f, hyperframe.frame.Frame)
