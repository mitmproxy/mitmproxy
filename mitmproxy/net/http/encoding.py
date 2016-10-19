"""
Utility functions for decoding response bodies.
"""

import codecs
import collections
from io import BytesIO

import gzip
import zlib
import brotli

from typing import Union


# We have a shared single-element cache for encoding and decoding.
# This is quite useful in practice, e.g.
# flow.request.content = flow.request.content.replace(b"foo", b"bar")
# does not require an .encode() call if content does not contain b"foo"
CachedDecode = collections.namedtuple("CachedDecode", "encoded encoding errors decoded")
_cache = CachedDecode(None, None, None, None)


def decode(encoded: Union[str, bytes], encoding: str, errors: str='strict') -> Union[str, bytes]:
    """
    Decode the given input object

    Returns:
        The decoded value

    Raises:
        ValueError, if decoding fails.
    """
    if len(encoded) == 0:
        return encoded

    global _cache
    cached = (
        isinstance(encoded, bytes) and
        _cache.encoded == encoded and
        _cache.encoding == encoding and
        _cache.errors == errors
    )
    if cached:
        return _cache.decoded
    try:
        try:
            decoded = custom_decode[encoding](encoded)
        except KeyError:
            decoded = codecs.decode(encoded, encoding, errors)
        if encoding in ("gzip", "deflate", "br"):
            _cache = CachedDecode(encoded, encoding, errors, decoded)
        return decoded
    except TypeError:
        raise
    except Exception as e:
        raise ValueError("{} when decoding {} with {}: {}".format(
            type(e).__name__,
            repr(encoded)[:10],
            repr(encoding),
            repr(e),
        ))


def encode(decoded: Union[str, bytes], encoding: str, errors: str='strict') -> Union[str, bytes]:
    """
    Encode the given input object

    Returns:
        The encoded value

    Raises:
        ValueError, if encoding fails.
    """
    if len(decoded) == 0:
        return decoded

    global _cache
    cached = (
        isinstance(decoded, bytes) and
        _cache.decoded == decoded and
        _cache.encoding == encoding and
        _cache.errors == errors
    )
    if cached:
        return _cache.encoded
    try:
        try:
            value = decoded
            if isinstance(value, str):
                value = decoded.encode()
            encoded = custom_encode[encoding](value)
        except KeyError:
            encoded = codecs.encode(decoded, encoding, errors)
        if encoding in ("gzip", "deflate", "br"):
            _cache = CachedDecode(encoded, encoding, errors, decoded)
        return encoded
    except TypeError:
        raise
    except Exception as e:
        raise ValueError("{} when encoding {} with {}: {}".format(
            type(e).__name__,
            repr(decoded)[:10],
            repr(encoding),
            repr(e),
        ))


def identity(content):
    """
        Returns content unchanged. Identity is the default value of
        Accept-Encoding headers.
    """
    return content


def decode_gzip(content):
    gfile = gzip.GzipFile(fileobj=BytesIO(content))
    return gfile.read()


def encode_gzip(content):
    s = BytesIO()
    gf = gzip.GzipFile(fileobj=s, mode='wb')
    gf.write(content)
    gf.close()
    return s.getvalue()


def decode_brotli(content):
    return brotli.decompress(content)


def encode_brotli(content):
    return brotli.compress(content)


def decode_deflate(content):
    """
        Returns decompressed data for DEFLATE. Some servers may respond with
        compressed data without a zlib header or checksum. An undocumented
        feature of zlib permits the lenient decompression of data missing both
        values.

        http://bugs.python.org/issue5784
    """
    try:
        return zlib.decompress(content)
    except zlib.error:
        return zlib.decompress(content, -15)


def encode_deflate(content):
    """
        Returns compressed content, always including zlib header and checksum.
    """
    return zlib.compress(content)


custom_decode = {
    "none": identity,
    "identity": identity,
    "gzip": decode_gzip,
    "deflate": decode_deflate,
    "br": decode_brotli,
}
custom_encode = {
    "none": identity,
    "identity": identity,
    "gzip": encode_gzip,
    "deflate": encode_deflate,
    "br": encode_brotli,
}

__all__ = ["encode", "decode"]
