import re
import time
from collections.abc import Iterable

from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.net.http import url


def get_header_tokens(headers, key):
    """
    Retrieve all tokens for a header key. A number of different headers
    follow a pattern where each header line can containe comma-separated
    tokens, and headers can be set multiple times.
    """
    if key not in headers:
        return []
    tokens = headers[key].split(",")
    return [token.strip() for token in tokens]


def connection_close(http_version, headers):
    """
    Checks the message to see if the client connection should be closed
    according to RFC 2616 Section 8.1.
    If we don't have a Connection header, HTTP 1.1 connections are assumed
    to be persistent.
    """
    if "connection" in headers:
        tokens = get_header_tokens(headers, "connection")
        if "close" in tokens:
            return True
        elif "keep-alive" in tokens:
            return False

    return http_version not in (
        "HTTP/1.1",
        b"HTTP/1.1",
        "HTTP/2.0",
        b"HTTP/2.0",
    )


# https://datatracker.ietf.org/doc/html/rfc7230#section-3.2: Header fields are tokens.
# "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /  "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
_valid_header_name = re.compile(rb"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$")


def validate_headers(headers: Headers) -> None:
    """
    Validate headers to avoid request smuggling attacks. Raises a ValueError if they are malformed.
    """

    te_found = False
    cl_found = False

    for name, value in headers.fields:
        if not _valid_header_name.match(name):
            raise ValueError(
                f"Received an invalid header name: {name!r}. Invalid header names may introduce "
                f"request smuggling vulnerabilities. Disable the validate_inbound_headers option "
                f"to skip this security check."
            )

        name_lower = name.lower()
        te_found = te_found or name_lower == b"transfer-encoding"
        cl_found = cl_found or name_lower == b"content-length"

    if te_found and cl_found:
        raise ValueError(
            "Received both a Transfer-Encoding and a Content-Length header, "
            "refusing as recommended in RFC 7230 Section 3.3.3. "
            "See https://github.com/mitmproxy/mitmproxy/issues/4799 for details. "
            "Disable the validate_inbound_headers option to skip this security check."
        )


def expected_http_body_size(
    request: Request, response: Response | None = None
) -> int | None:
    """
    Returns:
        The expected body length:
        - a positive integer, if the size is known in advance
        - None, if the size in unknown in advance (chunked encoding)
        - -1, if all data should be read until end of stream.

    Raises:
        ValueError, if the content length header is invalid
    """
    # Determine response size according to http://tools.ietf.org/html/rfc7230#section-3.3, which is inlined below.
    if not response:
        headers = request.headers
    else:
        headers = response.headers

        #    1.  Any response to a HEAD request and any response with a 1xx
        #        (Informational), 204 (No Content), or 304 (Not Modified) status
        #        code is always terminated by the first empty line after the
        #        header fields, regardless of the header fields present in the
        #        message, and thus cannot contain a message body.
        if request.method.upper() == "HEAD":
            return 0
        if 100 <= response.status_code <= 199:
            return 0
        if response.status_code in (204, 304):
            return 0

        #    2.  Any 2xx (Successful) response to a CONNECT request implies that
        #        the connection will become a tunnel immediately after the empty
        #        line that concludes the header fields.  A client MUST ignore any
        #        Content-Length or Transfer-Encoding header fields received in
        #        such a message.
        if 200 <= response.status_code <= 299 and request.method.upper() == "CONNECT":
            return 0

    #    3.  If a Transfer-Encoding header field is present and the chunked
    #        transfer coding (Section 4.1) is the final encoding, the message
    #        body length is determined by reading and decoding the chunked
    #        data until the transfer coding indicates the data is complete.
    #
    #        If a Transfer-Encoding header field is present in a response and
    #        the chunked transfer coding is not the final encoding, the
    #        message body length is determined by reading the connection until
    #        it is closed by the server.  If a Transfer-Encoding header field
    #        is present in a request and the chunked transfer coding is not
    #        the final encoding, the message body length cannot be determined
    #        reliably; the server MUST respond with the 400 (Bad Request)
    #        status code and then close the connection.
    #
    #        If a message is received with both a Transfer-Encoding and a
    #        Content-Length header field, the Transfer-Encoding overrides the
    #        Content-Length.  Such a message might indicate an attempt to
    #        perform request smuggling (Section 9.5) or response splitting
    #        (Section 9.4) and ought to be handled as an error.  A sender MUST
    #        remove the received Content-Length field prior to forwarding such
    #        a message downstream.
    #
    if "transfer-encoding" in headers:
        # we should make sure that there isn't also a content-length header.
        # this is already handled in validate_headers.

        te: str = headers["transfer-encoding"]
        if not te.isascii():
            # guard against .lower() transforming non-ascii to ascii
            raise ValueError(f"Invalid transfer encoding: {te!r}")
        te = te.lower().strip("\t ")
        te = re.sub(r"[\t ]*,[\t ]*", ",", te)
        if te in (
            "chunked",
            "compress,chunked",
            "deflate,chunked",
            "gzip,chunked",
        ):
            return None
        elif te in (
            "compress",
            "deflate",
            "gzip",
            "identity",
        ):
            if response:
                return -1
            else:
                raise ValueError(
                    f"Invalid request transfer encoding, message body cannot be determined reliably."
                )
        else:
            raise ValueError(
                f"Unknown transfer encoding: {headers['transfer-encoding']!r}"
            )

    #    4.  If a message is received without Transfer-Encoding and with
    #        either multiple Content-Length header fields having differing
    #        field-values or a single Content-Length header field having an
    #        invalid value, then the message framing is invalid and the
    #        recipient MUST treat it as an unrecoverable error.  If this is a
    #        request message, the server MUST respond with a 400 (Bad Request)
    #        status code and then close the connection.  If this is a response
    #        message received by a proxy, the proxy MUST close the connection
    #        to the server, discard the received response, and send a 502 (Bad
    #        Gateway) response to the client.  If this is a response message
    #        received by a user agent, the user agent MUST close the
    #        connection to the server and discard the received response.
    #
    #    5.  If a valid Content-Length header field is present without
    #        Transfer-Encoding, its decimal value defines the expected message
    #        body length in octets.  If the sender closes the connection or
    #        the recipient times out before the indicated number of octets are
    #        received, the recipient MUST consider the message to be
    #        incomplete and close the connection.
    if "content-length" in headers:
        sizes = headers.get_all("content-length")
        different_content_length_headers = any(x != sizes[0] for x in sizes)
        if different_content_length_headers:
            raise ValueError(f"Conflicting Content-Length headers: {sizes!r}")
        try:
            size = int(sizes[0])
        except ValueError:
            raise ValueError(f"Invalid Content-Length header: {sizes[0]!r}")
        if size < 0:
            raise ValueError(f"Negative Content-Length header: {sizes[0]!r}")
        return size

    #    6.  If this is a request message and none of the above are true, then
    #        the message body length is zero (no message body is present).
    if not response:
        return 0

    #    7.  Otherwise, this is a response message without a declared message
    #        body length, so the message body length is determined by the
    #        number of octets received prior to the server closing the
    #        connection.
    return -1


def raise_if_http_version_unknown(http_version: bytes) -> None:
    if not re.match(rb"^HTTP/\d\.\d$", http_version):
        raise ValueError(f"Unknown HTTP version: {http_version!r}")


def _read_request_line(
    line: bytes,
) -> tuple[str, int, bytes, bytes, bytes, bytes, bytes]:
    try:
        method, target, http_version = line.split()
        port: int | None

        if target == b"*" or target.startswith(b"/"):
            scheme, authority, path = b"", b"", target
            host, port = "", 0
        elif method == b"CONNECT":
            scheme, authority, path = b"", target, b""
            host, port = url.parse_authority(authority, check=True)
            if not port:
                raise ValueError
        else:
            scheme, rest = target.split(b"://", maxsplit=1)
            authority, _, path_ = rest.partition(b"/")
            path = b"/" + path_
            host, port = url.parse_authority(authority, check=True)
            port = port or url.default_port(scheme)
            if not port:
                raise ValueError
            # TODO: we can probably get rid of this check?
            url.parse(target)

        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP request line: {line!r}") from e

    return host, port, method, scheme, authority, path, http_version


def _read_response_line(line: bytes) -> tuple[bytes, int, bytes]:
    try:
        parts = line.split(None, 2)
        if len(parts) == 2:  # handle missing message gracefully
            parts.append(b"")

        http_version, status_code_str, reason = parts
        status_code = int(status_code_str)
        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP response line: {line!r}") from e

    return http_version, status_code, reason


def _read_headers(lines: Iterable[bytes]) -> Headers:
    """
    Read a set of headers.
    Stop once a blank line is reached.

    Returns:
        A headers object

    Raises:
        exceptions.HttpSyntaxException
    """
    ret: list[tuple[bytes, bytes]] = []
    for line in lines:
        if line[0] in b" \t":
            if not ret:
                raise ValueError("Invalid headers")
            # continued header
            ret[-1] = (ret[-1][0], ret[-1][1] + b"\r\n " + line.strip())
        else:
            try:
                name, value = line.split(b":", 1)
                value = value.strip()
                if not name:
                    raise ValueError()
                ret.append((name, value))
            except ValueError:
                raise ValueError(f"Invalid header line: {line!r}")
    return Headers(ret)


def read_request_head(lines: list[bytes]) -> Request:
    """
    Parse an HTTP request head (request line + headers) from an iterable of lines

    Args:
        lines: The input lines

    Returns:
        The HTTP request object (without body)

    Raises:
        ValueError: The input is malformed.
    """
    host, port, method, scheme, authority, path, http_version = _read_request_line(
        lines[0]
    )
    headers = _read_headers(lines[1:])

    return Request(
        host=host,
        port=port,
        method=method,
        scheme=scheme,
        authority=authority,
        path=path,
        http_version=http_version,
        headers=headers,
        content=None,
        trailers=None,
        timestamp_start=time.time(),
        timestamp_end=None,
    )


def read_response_head(lines: list[bytes]) -> Response:
    """
    Parse an HTTP response head (response line + headers) from an iterable of lines

    Args:
        lines: The input lines

    Returns:
        The HTTP response object (without body)

    Raises:
        ValueError: The input is malformed.
    """
    http_version, status_code, reason = _read_response_line(lines[0])
    headers = _read_headers(lines[1:])

    return Response(
        http_version=http_version,
        status_code=status_code,
        reason=reason,
        headers=headers,
        content=None,
        trailers=None,
        timestamp_start=time.time(),
        timestamp_end=None,
    )
