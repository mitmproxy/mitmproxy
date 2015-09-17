"""
    Utility functions for decoding response bodies.
"""
from __future__ import absolute_import
from io import BytesIO
import gzip
import zlib
from .utils import always_byte_args


ENCODINGS = {b"identity", b"gzip", b"deflate"}


@always_byte_args("ascii", "ignore")
def decode(e, content):
    encoding_map = {
        b"identity": identity,
        b"gzip": decode_gzip,
        b"deflate": decode_deflate,
    }
    if e not in encoding_map:
        return None
    return encoding_map[e](content)


@always_byte_args("ascii", "ignore")
def encode(e, content):
    encoding_map = {
        b"identity": identity,
        b"gzip": encode_gzip,
        b"deflate": encode_deflate,
    }
    if e not in encoding_map:
        return None
    return encoding_map[e](content)


def identity(content):
    """
        Returns content unchanged. Identity is the default value of
        Accept-Encoding headers.
    """
    return content


def decode_gzip(content):
    gfile = gzip.GzipFile(fileobj=BytesIO(content))
    try:
        return gfile.read()
    except (IOError, EOFError):
        return None


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
        try:
            return zlib.decompress(content)
        except zlib.error:
            return zlib.decompress(content, -15)
    except zlib.error:
        return None


def encode_deflate(content):
    """
        Returns compressed content, always including zlib header and checksum.
    """
    return zlib.compress(content)

__all__ = ["ENCODINGS", "encode", "decode"]
