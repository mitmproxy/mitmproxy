import re
import time
from typing import List, Tuple, Iterable, Optional

from mitmproxy.http import Request, Headers, Response
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
        "HTTP/1.1", b"HTTP/1.1",
        "HTTP/2.0", b"HTTP/2.0",
    )


def expected_http_body_size(
        request: Request,
        response: Optional[Response] = None
) -> Optional[int]:
    """
        Returns:
            The expected body length:
            - a positive integer, if the size is known in advance
            - None, if the size in unknown in advance (chunked encoding)
            - -1, if all data should be read until end of stream.

        Raises:
            ValueError, if the content length header is invalid
    """
    # Determine response size according to
    # http://tools.ietf.org/html/rfc7230#section-3.3
    if not response:
        headers = request.headers
        if request.method.upper() == "CONNECT":
            return 0
    else:
        headers = response.headers
        if request.method.upper() == "HEAD":
            return 0
        if 100 <= response.status_code <= 199:
            return 0
        if response.status_code == 200 and request.method.upper() == "CONNECT":
            return 0
        if response.status_code in (204, 304):
            return 0

    if "content-length" in headers:
        sizes = headers.get_all("content-length")
        different_content_length_headers = any(x != sizes[0] for x in sizes)
        if different_content_length_headers:
            raise ValueError("Conflicting Content Length Headers")
        size = int(sizes[0])
        if size < 0:
            raise ValueError("Negative Content Length")
        return size
    if "chunked" in headers.get("transfer-encoding", "").lower():
        return None
    if not response:
        return 0
    return -1


def raise_if_http_version_unknown(http_version: bytes) -> None:
    if not re.match(br"^HTTP/\d\.\d$", http_version):
        raise ValueError(f"Unknown HTTP version: {http_version!r}")


def _read_request_line(line: bytes) -> Tuple[str, int, bytes, bytes, bytes, bytes, bytes]:
    try:
        method, target, http_version = line.split()
        port: Optional[int]

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


def _read_response_line(line: bytes) -> Tuple[bytes, int, bytes]:
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
    ret: List[Tuple[bytes, bytes]] = []
    for line in lines:
        if line[0] in b" \t":
            if not ret:
                raise ValueError("Invalid headers")
            # continued header
            ret[-1] = (ret[-1][0], ret[-1][1] + b'\r\n ' + line.strip())
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


def read_request_head(lines: List[bytes]) -> Request:
    """
    Parse an HTTP request head (request line + headers) from an iterable of lines

    Args:
        lines: The input lines

    Returns:
        The HTTP request object (without body)

    Raises:
        ValueError: The input is malformed.
    """
    host, port, method, scheme, authority, path, http_version = _read_request_line(lines[0])
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
        timestamp_end=None
    )


def read_response_head(lines: List[bytes]) -> Response:
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
