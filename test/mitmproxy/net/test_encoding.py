from unittest import mock
import pytest

from mitmproxy.net import encoding


@pytest.mark.parametrize("encoder", [
    'identity',
    'none',
])
def test_identity(encoder):
    assert b"string" == encoding.decode(b"string", encoder)
    assert b"string" == encoding.encode(b"string", encoder)
    with pytest.raises(ValueError):
        encoding.encode(b"string", "nonexistent encoding")


@pytest.mark.parametrize("encoder", [
    'gzip',
    'br',
    'deflate',
    'zstd',
])
def test_encoders(encoder):
    """
        This test is for testing byte->byte encoding/decoding
    """
    assert encoding.decode(None, encoder) is None
    assert encoding.encode(None, encoder) is None

    assert b"" == encoding.decode(b"", encoder)

    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            encoder
        ),
        encoder
    )

    with pytest.raises(TypeError):
        encoding.encode("string", encoder)

    with pytest.raises(TypeError):
        encoding.decode("string", encoder)
    with pytest.raises(ValueError):
        encoding.decode(b"foobar", encoder)


@pytest.mark.parametrize("encoder", [
    'utf8',
    'latin-1'
])
def test_encoders_strings(encoder):
    """
        This test is for testing byte->str decoding
        and str->byte encoding
    """
    assert "" == encoding.decode(b"", encoder)

    assert "string" == encoding.decode(
        encoding.encode(
            "string",
            encoder
        ),
        encoder
    )

    with pytest.raises(TypeError):
        encoding.encode(b"string", encoder)

    with pytest.raises(TypeError):
        encoding.decode("foobar", encoder)


def test_cache():
    decode_gzip = mock.MagicMock()
    decode_gzip.return_value = b"decoded"
    encode_gzip = mock.MagicMock()
    encode_gzip.return_value = b"encoded"

    with mock.patch.dict(encoding.custom_decode, gzip=decode_gzip):
        with mock.patch.dict(encoding.custom_encode, gzip=encode_gzip):
            assert encoding.decode(b"encoded", "gzip") == b"decoded"
            assert decode_gzip.call_count == 1

            # should be cached
            assert encoding.decode(b"encoded", "gzip") == b"decoded"
            assert decode_gzip.call_count == 1

            # the other way around as well
            assert encoding.encode(b"decoded", "gzip") == b"encoded"
            assert encode_gzip.call_count == 0

            # different encoding
            decode_gzip.return_value = b"bar"
            assert encoding.encode(b"decoded", "deflate") != b"decoded"
            assert encode_gzip.call_count == 0

            # This is not in the cache anymore
            assert encoding.encode(b"decoded", "gzip") == b"encoded"
            assert encode_gzip.call_count == 1
