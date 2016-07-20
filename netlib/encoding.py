"""
Utility functions for decoding response bodies.
"""
from __future__ import absolute_import

import codecs
from io import BytesIO
import gzip
import zlib

from typing import Union  # noqa


def decode(obj, encoding, errors='strict'):
    # type: (Union[str, bytes], str, str) -> Union[str, bytes]
    """
    Decode the given input object

    Returns:
        The decoded value

    Raises:
        ValueError, if decoding fails.
    """
    try:
        try:
            return custom_decode[encoding](obj)
        except KeyError:
            return codecs.decode(obj, encoding, errors)
    except Exception as e:
        raise ValueError("{} when decoding {} with {}".format(
            type(e).__name__,
            repr(obj)[:10],
            repr(encoding),
        ))


def encode(obj, encoding, errors='strict'):
    # type: (Union[str, bytes], str, str) -> Union[str, bytes]
    """
    Encode the given input object

    Returns:
        The encoded value

    Raises:
        ValueError, if encoding fails.
    """
    try:
        try:
            return custom_encode[encoding](obj)
        except KeyError:
            return codecs.encode(obj, encoding, errors)
    except Exception as e:
        raise ValueError("{} when encoding {} with {}".format(
            type(e).__name__,
            repr(obj)[:10],
            repr(encoding),
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
    "identity": identity,
    "gzip": decode_gzip,
    "deflate": decode_deflate,
}
custom_encode = {
    "identity": identity,
    "gzip": encode_gzip,
    "deflate": encode_deflate,
}

__all__ = ["encode", "decode"]
