import logging
import re
import typing

from mitmproxy.http import Message
from mitmproxy.http import Request
from mitmproxy.http import Response

logger = logging.getLogger(__name__)

# https://datatracker.ietf.org/doc/html/rfc7230#section-3.2: Header fields are tokens.
# "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /  "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
_valid_header_name = re.compile(rb"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$")

_valid_content_length = re.compile(rb"^(?:0|[1-9][0-9]*)$")
_valid_content_length_str = re.compile(r"^(?:0|[1-9][0-9]*)$")

# https://datatracker.ietf.org/doc/html/rfc9112#section-6.1:
# > A sender MUST NOT apply the chunked transfer coding more than once to a message body (i.e., chunking an already
# > chunked message is not allowed). If any transfer coding other than chunked is applied to a request's content, the
# > sender MUST apply chunked as the final transfer coding to ensure that the message is properly framed. If any
# > transfer coding other than chunked is applied to a response's content, the sender MUST either apply chunked as the
# > final transfer coding or terminate the message by closing the connection.
#
# The RFC technically still allows for fun encodings, we are a bit stricter and only accept a known subset by default.
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
_HTTP_1_1_TRANSFER_ENCODINGS = frozenset(typing.get_args(TransferEncoding))


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
    if te not in _HTTP_1_1_TRANSFER_ENCODINGS:
        raise ValueError(f"unknown transfer-encoding header: {value!r}")
    return typing.cast(TransferEncoding, te)


def validate_headers(message: Message) -> None:
    """
    Validate HTTP message headers to avoid request smuggling attacks.

    Raises a ValueError if they are malformed.
    """

    te = []
    cl = []

    for name, value in message.headers.fields:
        if not _valid_header_name.match(name):
            raise ValueError(f"invalid header name: {name!r}")
        match name.lower():
            case b"transfer-encoding":
                te.append(value)
            case b"content-length":
                cl.append(value)

    if te and cl:
        # > A server MAY reject a request that contains both Content-Length and Transfer-Encoding or process such a
        # > request in accordance with the Transfer-Encoding alone.

        # > A sender MUST NOT send a Content-Length header field in any message that contains a Transfer-Encoding header
        # > field.
        raise ValueError(
            "message with both transfer-encoding and content-length headers"
        )
    elif te:
        if len(te) > 1:
            raise ValueError(f"multiple transfer-encoding headers: {te!r}")
        # > Transfer-Encoding was added in HTTP/1.1. It is generally assumed that implementations advertising only
        # > HTTP/1.0 support will not understand how to process transfer-encoded content, and that an HTTP/1.0 message
        # > received with a Transfer-Encoding is likely to have been forwarded without proper handling of the chunked
        # > transfer coding in transit.
        #
        # > A client MUST NOT send a request containing Transfer-Encoding unless it knows the server will handle
        # > HTTP/1.1 requests (or later minor revisions); such knowledge might be in the form of specific user
        # > configuration or by remembering the version of a prior received response. A server MUST NOT send a response
        # > containing Transfer-Encoding unless the corresponding request indicates HTTP/1.1 (or later minor revisions).
        if not message.is_http11:
            raise ValueError(
                f"unexpected HTTP transfer-encoding {te[0]!r} for {message.http_version}"
            )
        # > A server MUST NOT send a Transfer-Encoding header field in any response with a status code of 1xx
        # > (Informational) or 204 (No Content).
        if isinstance(message, Response) and (
            100 <= message.status_code <= 199 or message.status_code == 204
        ):
            raise ValueError(
                f"unexpected HTTP transfer-encoding {te[0]!r} for response with status code {message.status_code}"
            )
        # > If a Transfer-Encoding header field is present in a request and the chunked transfer coding is not the final
        # > encoding, the message body length cannot be determined reliably; the server MUST respond with the 400 (Bad
        # > Request) status code and then close the connection.
        te_parsed = parse_transfer_encoding(te[0])
        match te_parsed:
            case "chunked" | "compress,chunked" | "deflate,chunked" | "gzip,chunked":
                pass
            case "compress" | "deflate" | "gzip" | "identity":
                if isinstance(message, Request):
                    raise ValueError(
                        f"unexpected HTTP transfer-encoding {te_parsed!r} for request"
                    )
            case other:  # pragma: no cover
                typing.assert_never(other)
    elif cl:
        # > If a message is received without Transfer-Encoding and with an invalid Content-Length header field, then the
        # > message framing is invalid and the recipient MUST treat it as an unrecoverable error, unless the field value
        # > can be successfully parsed as a comma-separated list (Section 5.6.1 of [HTTP]), all values in the list are
        # > valid, and all values in the list are the same (in which case, the message is processed with that single
        # > value used as the Content-Length field value).
        # We are stricter here and reject comma-separated lists.
        if len(cl) > 1:
            raise ValueError(f"multiple content-length headers: {cl!r}")
        parse_content_length(cl[0])
