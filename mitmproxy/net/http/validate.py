import logging
import re
import typing
from typing import NoReturn

from mitmproxy.http import Headers

logger = logging.getLogger(__name__)

# https://datatracker.ietf.org/doc/html/rfc7230#section-3.2: Header fields are tokens.
# "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /  "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
_valid_header_name = re.compile(rb"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$")

_valid_content_length = re.compile(rb"^(?:0|[1-9][0-9]*)$")
_valid_content_length_str = re.compile(r"^(?:0|[1-9][0-9]*)$")

TransferEncoding = typing.Literal[
    "chunked",
    "compress,chunked",
    "deflate,chunked",
    "gzip,chunked",
    "compress",
    "deflate",
    "gzip",
    "identity",
]
_TRANSFER_ENCODINGS = frozenset(typing.get_args(TransferEncoding))


def parse_content_length(value: str | bytes) -> int:
    """Parse a content-length header value, or raise a ValueError if it is invalid."""
    if isinstance(value, str):
        valid = bool(_valid_content_length_str.match(value))
    else:
        valid = bool(_valid_content_length.match(value))
    if not valid:
        raise ValueError(f"invalid content-length header: {value!r}")
    return int(value)


def parse_transfer_encoding(value: str | bytes) -> TransferEncoding:
    """Parse a transfer-encoding header value, or raise a ValueError if it is invalid or unknown."""
    # guard against .lower() transforming non-ascii to ascii
    if not value.isascii():
        raise ValueError(f"invalid transfer-encoding header: {value!r}")
    if isinstance(value, str):
        te = value
    else:
        te = value.decode()
    te = te.lower()
    te = re.sub(r"[\t ]*,[\t ]*", ",", te)
    if te not in _TRANSFER_ENCODINGS:
        raise ValueError(f"unknown transfer-encoding header: {value!r}")
    return typing.cast(TransferEncoding, te)


def validate_headers(headers: Headers) -> None:
    """
    Validate headers to avoid request smuggling attacks.

    Raises a ValueError if they are malformed.
    """

    te = []
    cl = []

    for name, value in headers.fields:
        if not _valid_header_name.match(name):
            raise ValueError(f"invalid header name: {name!r}")
        match name.lower():
            case b"transfer-encoding":
                te.append(value)
            case b"content-length":
                cl.append(value)

    if te and cl:
        raise ValueError(
            "message with both transfer-encoding and content-length headers"
        )
    elif te:
        if len(te) > 1:
            raise ValueError(f"multiple transfer-encoding headers: {te!r}")
        parse_transfer_encoding(te[0])
    elif cl:
        if len(cl) > 1:
            raise ValueError(f"multiple content-length headers: {cl!r}")
        parse_content_length(cl[0])
