from unittest import mock

import pytest

from mitmproxy.net import encoding


@pytest.mark.parametrize(
    "encoder",
    [
        "identity",
        "none",
    ],
)
def test_identity(encoder):
    assert b"string" == encoding.decode(b"string", encoder)
    assert b"string" == encoding.encode(b"string", encoder)
    with pytest.raises(ValueError):
        encoding.encode(b"string", "nonexistent encoding")


@pytest.mark.parametrize(
    "encoder",
    [
        "gzip",
        "GZIP",
        "br",
        "deflate",
        "zstd",
    ],
)
def test_encoders(encoder):
    """
    This test is for testing byte->byte encoding/decoding
    """
    assert encoding.decode(None, encoder) is None
    assert encoding.encode(None, encoder) is None

    assert b"" == encoding.decode(b"", encoder)

    assert b"string" == encoding.decode(encoding.encode(b"string", encoder), encoder)

    with pytest.raises(TypeError):
        encoding.encode("string", encoder)

    with pytest.raises(TypeError):
        encoding.decode("string", encoder)
    with pytest.raises(ValueError):
        encoding.decode(b"foobar", encoder)


@pytest.mark.parametrize("encoder", ["utf8", "latin-1"])
def test_encoders_strings(encoder):
    """
    This test is for testing byte->str decoding
    and str->byte encoding
    """
    assert "" == encoding.decode(b"", encoder)

    assert "string" == encoding.decode(encoding.encode("string", encoder), encoder)

    with pytest.raises(TypeError):
        encoding.encode(b"string", encoder)

    with pytest.raises(TypeError):
        encoding.decode("foobar", encoder)


def test_decode_gzip_truncated():
    """
    Regression test for issue #7795: ensure decode_gzip() handles the real
    malformed/truncated gzip sample posted in the issue comments and does not
    raise. Using the exact test vector from the issue makes the test stable.
    """
    data = bytes.fromhex(
        "1f8b08000000000000ffaa564a2d2a72ce4f4955b2d235d551502a4a2df12d4e57"
        "b2527ab17efbb38d4d4f7b5a9fec58fb6cd3c267733a934a3353946a01000000ffff"
    )
    result = encoding.decode_gzip(data)

    assert isinstance(result, (bytes, bytearray))
    assert len(result) > 0


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


def test_zstd():
    FRAME_SIZE = 1024

    # Create payload of 1024b
    test_content = "a" * FRAME_SIZE

    # Compress it, will result a single frame
    single_frame = encoding.encode_zstd(test_content.encode())

    # Concat compressed frame, it'll result two frames, total size of 2048b payload
    two_frames = single_frame + single_frame

    # Uncompressed single frame should have the size of FRAME_SIZE
    assert len(encoding.decode_zstd(single_frame)) == FRAME_SIZE

    # Uncompressed two frames should have the size of FRAME_SIZE * 2
    assert len(encoding.decode_zstd(two_frames)) == FRAME_SIZE * 2
