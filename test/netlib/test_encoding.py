import mock
from netlib import encoding, tutils


def test_identity():
    assert b"string" == encoding.decode(b"string", "identity")
    assert b"string" == encoding.encode(b"string", "identity")
    with tutils.raises(ValueError):
        encoding.encode(b"string", "nonexistent encoding")


def test_gzip():
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "gzip"
        ),
        "gzip"
    )
    with tutils.raises(ValueError):
        encoding.decode(b"bogus", "gzip")


def test_brotli():
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "br"
        ),
        "br"
    )
    with tutils.raises(ValueError):
        encoding.decode(b"bogus", "br")


def test_deflate():
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "deflate"
        ),
        "deflate"
    )
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "deflate"
        )[2:-4],
        "deflate"
    )
    with tutils.raises(ValueError):
        encoding.decode(b"bogus", "deflate")


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
