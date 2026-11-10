from unittest import mock

import brotli
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


class TestDecodeGzip:
    def test_regular_gzip(self):
        # generated with gzip.compress(b"mitmproxy")
        data = bytes.fromhex(
            "1f8b0800e4a4106902ffcbcd2cc92d28caafa80400d21f9c9d09000000"
        )
        assert encoding.decode_gzip(data) == b"mitmproxy"

    def test_zlib(self):
        # generated with zlib.compress(b"mitmproxy")
        data = bytes.fromhex("789ccbcd2cc92d28caafa80400138e03fa")
        assert encoding.decode_gzip(data) == b"mitmproxy"

    def test_truncated(self):
        """https://github.com/mitmproxy/mitmproxy/issues/7795"""
        data = bytes.fromhex(
            "1f8b08000000000000ffaa564a2d2a72ce4f4955b2d235d551502a4a2df12d4e57"
            "b2527ab17efbb38d4d4f7b5a9fec58fb6cd3c267733a934a3353946a01000000ffff"
        )
        assert encoding.decode_gzip(data) == (
            b'{"errCode":-5, "retMsg":"\xe8\xaf\xb7\xe6\xb1\x82\xe5\x8c\x85\xe4'
            b'\xb8\xad\xe6\xb2\xa1\xe6\x9c\x89buid"}'
        )


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


@pytest.mark.parametrize("encoder", ["gzip", "deflate", "br", "zstd"])
def test_decode_size_limit(monkeypatch, encoder):
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 1024)
    compressed = encoding.encode(b"a" * 1025, encoder)
    encoding._cache = encoding.CachedDecode(None, None, None, None)

    with pytest.raises(ValueError, match="maximum size"):
        encoding.decode(compressed, encoder)


@pytest.mark.parametrize("encoder", ["gzip", "deflate", "br", "zstd"])
def test_decode_size_limit_exact(monkeypatch, encoder):
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 1024)
    compressed = encoding.encode(b"a" * 1024, encoder)
    encoding._cache = encoding.CachedDecode(None, None, None, None)

    assert encoding.decode(compressed, encoder) == b"a" * 1024


@pytest.mark.parametrize("encoder", ["gzip", "deflate", "br", "zstd"])
def test_decode_size_limit_disabled(monkeypatch, encoder):
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", None)
    compressed = encoding.encode(b"a" * 1025, encoder)
    encoding._cache = encoding.CachedDecode(None, None, None, None)

    assert len(encoding.decode(compressed, encoder)) == 1025


def test_zstd_concatenated_frames_size_limit(monkeypatch):
    single_frame = encoding.encode_zstd(b"a" * 1024)
    two_frames = single_frame + single_frame

    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 2048)
    assert len(encoding.decode_zstd(two_frames)) == 2048

    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 2047)
    with pytest.raises(ValueError, match="maximum size"):
        encoding.decode_zstd(two_frames)


def test_zstd_truncated(monkeypatch):
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 1024)
    compressed = encoding.encode_zstd(b"a" * 100)

    with pytest.raises(ValueError, match="incomplete zstd frame"):
        encoding.decode_zstd(compressed[:-2])


def test_brotli_truncated(monkeypatch):
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 1024)
    compressed = encoding.encode_brotli(b"a" * 100)

    with pytest.raises(ValueError, match="incomplete brotli stream"):
        encoding.decode_brotli(compressed[:-2])


@pytest.mark.parametrize("limit", [1024 * 1024, 9 * 1024 * 1024])
def test_brotli_decompression_bomb(monkeypatch, limit):
    # A few hundred bytes of brotli data expand to 10 MB here. The decoder
    # must stop once the limit is exceeded instead of buffering everything.
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", limit)
    bomb = brotli.compress(b"\x00" * (10 * 1024 * 1024), quality=5)
    assert len(bomb) < 1024

    with pytest.raises(ValueError, match="maximum size"):
        encoding.decode_brotli(bomb)


def test_brotli_buffered_output(monkeypatch):
    # The decoder buffers output when its internal buffer fills up, so a
    # larger body is drained in several process() calls.
    monkeypatch.setattr(encoding, "MAX_DECODED_SIZE", 100 * 1024 * 1024)
    plain = b"\x00" * (10 * 1024 * 1024)
    compressed = brotli.compress(plain, quality=5)

    assert encoding.decode_brotli(compressed) == plain
