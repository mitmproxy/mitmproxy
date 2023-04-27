"""
Utility functions for decoding response bodies.
"""

import codecs
import collections
import gzip
import zlib
from io import BytesIO
from typing import Union, overload

import brotli
import zstandard as zstd

# We have a shared single-element cache for encoding and decoding.
# This is quite useful in practice, e.g.
# flow.request.content = flow.request.content.replace(b"foo", b"bar")
# does not require an .encode() call if content does not contain b"foo"
CachedDecode = collections.namedtuple("CachedDecode", "encoded encoding errors decoded")
_cache = CachedDecode(None, None, None, None)


@overload
def decode(encoded: None, encoding: str, errors: str = "strict") -> None:
    ...


@overload
def decode(encoded: str, encoding: str, errors: str = "strict") -> str:
    ...


@overload
def decode(encoded: bytes, encoding: str, errors: str = "strict") -> Union[str, bytes]:
    ...


def decode(
    encoded: Union[None, str, bytes], encoding: str, errors: str = "strict"
) -> Union[None, str, bytes]:
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
def encode(decoded: None, encoding: str, errors: str = "strict") -> None:
    ...


@overload
def encode(decoded: str, encoding: str, errors: str = "strict") -> Union[str, bytes]:
    ...


@overload
def encode(decoded: bytes, encoding: str, errors: str = "strict") -> bytes:
    ...


def encode(
    decoded: Union[None, str, bytes], encoding, errors="strict"
) -> Union[None, str, bytes]:
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


def decode_gzip(content: bytes) -> bytes:
    if not content:
        return b""
    gfile = gzip.GzipFile(fileobj=BytesIO(content))
    return gfile.read()


def encode_gzip(content: bytes) -> bytes:
    s = BytesIO()
    gf = gzip.GzipFile(fileobj=s, mode="wb")
    gf.write(content)
    gf.close()
    return s.getvalue()


def decode_brotli(content: bytes) -> bytes:
    if not content:
        return b""
    return brotli.decompress(content)


def encode_brotli(content: bytes) -> bytes:
    return brotli.compress(content)


def decode_zstd(content: bytes) -> bytes:
    if not content:
        return b""
    zstd_ctx = zstd.ZstdDecompressor()
    try:
        return zstd_ctx.decompress(content)
    except zstd.ZstdError:
        # If the zstd stream is streamed without a size header,
        # try decoding with a 10MiB output buffer
        return zstd_ctx.decompress(content, max_output_size=10 * 2 ** 20)


def encode_zstd(content: bytes) -> bytes:
    zstd_ctx = zstd.ZstdCompressor()
    return zstd_ctx.compress(content)


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
        return zlib.decompress(content)
    except zlib.error:
        return zlib.decompress(content, -15)


def encode_deflate(content: bytes) -> bytes:
    """
    Returns compressed content, always including zlib header and checksum.
    """
    return zlib.compress(content)


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
