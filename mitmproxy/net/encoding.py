"""
Utility functions for decoding response bodies.
"""

import codecs
import collections
import gzip
import sys
import zlib
from io import BytesIO
from typing import overload

import brotli

if sys.version_info >= (3, 14):
    from compression import zstd
else:  # pragma: no cover
    from backports import zstd

# We have a shared single-element cache for encoding and decoding.
# This is quite useful in practice, e.g.
# flow.request.content = flow.request.content.replace(b"foo", b"bar")
# does not require an .encode() call if content does not contain b"foo"
CachedDecode = collections.namedtuple("CachedDecode", "encoded encoding errors decoded")
_cache = CachedDecode(None, None, None, None)

# Maximum size of decompressed data. This protects against decompression
# bombs, where a small compressed body expands to an arbitrarily large
# amount of data. The limit is configurable through the `max_decoded_size`
# option and can be set to `None` to disable it.
MAX_DECODED_SIZE: int | None = 100 * 1024 * 1024


@overload
def decode(encoded: None, encoding: str, errors: str = "strict") -> None: ...


@overload
def decode(encoded: str, encoding: str, errors: str = "strict") -> str: ...


@overload
def decode(encoded: bytes, encoding: str, errors: str = "strict") -> str | bytes: ...


def decode(
    encoded: None | str | bytes, encoding: str, errors: str = "strict"
) -> None | str | bytes:
    """
    Decode the given input object

    Returns:
        The decoded value

    Raises:
        ValueError, if decoding fails.
    """
    if encoded is None:
        return None
    encoding = encoding.lower()

    global _cache
    cached = (
        isinstance(encoded, bytes)
        and _cache.encoded == encoded
        and _cache.encoding == encoding
        and _cache.errors == errors
    )
    if cached:
        return _cache.decoded
    try:
        try:
            decoded = custom_decode[encoding](encoded)
        except KeyError:
            decoded = codecs.decode(encoded, encoding, errors)  # type: ignore
        if encoding in ("gzip", "deflate", "deflateraw", "br", "zstd"):
            _cache = CachedDecode(encoded, encoding, errors, decoded)
        return decoded
    except TypeError:
        raise
    except Exception as e:
        raise ValueError(
            "{} when decoding {} with {}: {}".format(
                type(e).__name__,
                repr(encoded)[:10],
                repr(encoding),
                repr(e),
            )
        )


@overload
def encode(decoded: None, encoding: str, errors: str = "strict") -> None: ...


@overload
def encode(decoded: str, encoding: str, errors: str = "strict") -> str | bytes: ...


@overload
def encode(decoded: bytes, encoding: str, errors: str = "strict") -> bytes: ...


def encode(
    decoded: None | str | bytes, encoding, errors="strict"
) -> None | str | bytes:
    """
    Encode the given input object

    Returns:
        The encoded value

    Raises:
        ValueError, if encoding fails.
    """
    if decoded is None:
        return None
    encoding = encoding.lower()

    global _cache
    cached = (
        isinstance(decoded, bytes)
        and _cache.decoded == decoded
        and _cache.encoding == encoding
        and _cache.errors == errors
    )
    if cached:
        return _cache.encoded
    try:
        try:
            encoded = custom_encode[encoding](decoded)
        except KeyError:
            encoded = codecs.encode(decoded, encoding, errors)  # type: ignore
        if encoding in ("gzip", "deflate", "deflateraw", "br", "zstd"):
            _cache = CachedDecode(encoded, encoding, errors, decoded)
        return encoded
    except TypeError:
        raise
    except Exception as e:
        raise ValueError(
            "{} when encoding {} with {}: {}".format(
                type(e).__name__,
                repr(decoded)[:10],
                repr(encoding),
                repr(e),
            )
        )


def identity(content):
    """
    Returns content unchanged. Identity is the default value of
    Accept-Encoding headers.
    """
    return content


def _size_limit_error() -> ValueError:
    return ValueError(
        f"Decompressed content exceeds the maximum size of {MAX_DECODED_SIZE} bytes."
    )


def _decompress_zlib(wbits: int, content: bytes) -> bytes:
    decompressor = zlib.decompressobj(wbits)
    if MAX_DECODED_SIZE is None:
        return decompressor.decompress(content) + decompressor.flush()

    # Ask for one byte more than the limit so we can distinguish content
    # that fits exactly from content that does not.
    out = decompressor.decompress(content, MAX_DECODED_SIZE + 1)
    if len(out) > MAX_DECODED_SIZE or decompressor.unconsumed_tail:
        raise _size_limit_error()
    return out + decompressor.flush()


def decode_gzip(content: bytes) -> bytes:
    """Decode gzip or zlib-compressed data using zlib's auto-detection."""
    if not content:
        return b""

    try:
        # Using wbits=47 (32 + 15) tells zlib to automatically detect both gzip and zlib headers.
        # This simplifies decoding and avoids the need for a separate gzip.GzipFile fallback.
        # Reference: https://docs.python.org/3/library/zlib.html#zlib.decompress
        return _decompress_zlib(47, content)
    except zlib.error as e:
        raise ValueError(f"Decompression failed: {e}")


def encode_gzip(content: bytes) -> bytes:
    s = BytesIO()
    # set mtime to 0 so that gzip encoding is deterministic.
    # Use compresslevel=1 for fastest compression speed.
    with gzip.GzipFile(fileobj=s, mode="wb", mtime=0, compresslevel=1) as f:
        f.write(content)
    return s.getvalue()


def decode_brotli(content: bytes) -> bytes:
    if not content:
        return b""
    if MAX_DECODED_SIZE is None:
        return brotli.decompress(content)

    decompressor = brotli.Decompressor()
    # Limit the decoder's internal output buffer. Without this, a tiny
    # compressed body can expand to hundreds of megabytes in a single
    # process() call before we get a chance to check MAX_DECODED_SIZE.
    buffer_limit = min(64 * 1024, MAX_DECODED_SIZE + 1)
    out = bytearray()

    def drain() -> None:
        # The decoder buffers output once the buffer limit is reached.
        # Drain it with empty input before feeding more data.
        while not decompressor.can_accept_more_data():
            before = len(out)
            out.extend(decompressor.process(b"", buffer_limit))
            if len(out) > MAX_DECODED_SIZE:
                raise _size_limit_error()
            if len(out) == before:  # pragma: no cover
                raise ValueError("Decompression failed: incomplete brotli stream")

    chunk_size = 8192
    for i in range(0, len(content), chunk_size):
        out.extend(decompressor.process(content[i : i + chunk_size], buffer_limit))
        if len(out) > MAX_DECODED_SIZE:
            raise _size_limit_error()
        drain()

    while not decompressor.is_finished():
        more = decompressor.process(b"", buffer_limit)
        if not more:
            raise ValueError("Decompression failed: incomplete brotli stream")
        out.extend(more)
        if len(out) > MAX_DECODED_SIZE:
            raise _size_limit_error()
    return bytes(out)


def encode_brotli(content: bytes) -> bytes:
    # Use quality=0 for fastest compression speed.
    return brotli.compress(content, quality=0)


def decode_zstd(content: bytes) -> bytes:
    if not content:
        return b""
    if MAX_DECODED_SIZE is None:
        return zstd.decompress(content)

    out = bytearray()
    remaining = content
    while remaining:
        decompressor = zstd.ZstdDecompressor()
        max_length = MAX_DECODED_SIZE - len(out) + 1
        out.extend(decompressor.decompress(remaining, max_length=max_length))
        if len(out) > MAX_DECODED_SIZE:
            raise _size_limit_error()
        if not decompressor.eof:
            raise ValueError("Decompression failed: incomplete zstd frame")
        remaining = decompressor.unused_data
    return bytes(out)


def encode_zstd(content: bytes) -> bytes:
    # Use level=1 for fastest compression speed.
    return zstd.compress(content, level=1)


def decode_deflate(content: bytes) -> bytes:
    """
    Returns decompressed data for DEFLATE. Some servers may respond with
    compressed data without a zlib header or checksum. An undocumented
    feature of zlib permits the lenient decompression of data missing both
    values.

    http://bugs.python.org/issue5784
    """
    if not content:
        return b""
    try:
        return _decompress_zlib(15, content)
    except zlib.error:
        return _decompress_zlib(-15, content)


def encode_deflate(content: bytes) -> bytes:
    """
    Returns compressed content, always including zlib header and checksum.
    """
    # Use level=1 for fastest compression speed.
    return zlib.compress(content, level=1)


custom_decode = {
    "none": identity,
    "identity": identity,
    "gzip": decode_gzip,
    "deflate": decode_deflate,
    "deflateraw": decode_deflate,
    "br": decode_brotli,
    "zstd": decode_zstd,
}
custom_encode = {
    "none": identity,
    "identity": identity,
    "gzip": encode_gzip,
    "deflate": encode_deflate,
    "deflateraw": encode_deflate,
    "br": encode_brotli,
    "zstd": encode_zstd,
}

__all__ = ["encode", "decode"]
