import re
import time
from typing import Iterable, List, Optional, Tuple

from mitmproxy.net import check
from mitmproxy.net.http import headers, request, response, url
from mitmproxy.net.http.http1 import read


def _parse_authority_form(hostport: bytes) -> Tuple[bytes, int]:
    """
        Returns (host, port) if hostport is a valid authority-form host specification.
        http://tools.ietf.org/html/draft-luotonen-web-proxy-tunneling-01 section 3.1

        Raises:
            ValueError, if the input is malformed
    """
    try:
        host, port = hostport.rsplit(b":", 1)
        if host.startswith(b"[") and host.endswith(b"]"):
            host = host[1:-1]
        port = int(port)
        if not check.is_valid_host(host) or not check.is_valid_port(port):
            raise ValueError
    except ValueError:
        raise ValueError(f"Invalid host specification: {hostport}")

    return host, port


def raise_if_http_version_unknown(http_version):
    if not re.match(br"^HTTP/\d\.\d$", http_version):
        raise ValueError(f"Unknown HTTP version: {http_version}")


def _read_request_line(line: bytes) -> Tuple[str, int, bytes, bytes, bytes, bytes, bytes]:
    try:
        method, target, http_version = line.split()

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
            authority, path_ = rest.split(b"/", maxsplit=1)
            path = b"/" + path_
            host, port = url.parse_authority(authority, check=True)
            port = port or url.default_port(scheme)
            if not port:
                raise ValueError
            # TODO: we can probably get rid of this check?
            url.parse(target)

        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP request line: {line}") from e

    return host, port, method, scheme, authority, path, http_version


def _read_response_line(line: bytes) -> Tuple[bytes, int, bytes]:
    try:
        parts = line.split(None, 2)
        if len(parts) == 2:  # handle missing message gracefully
            parts.append(b"")

        http_version, status_code, reason = parts
        status_code = int(status_code)
        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP response line: {line}") from e

    return http_version, status_code, reason


def _read_headers(lines: Iterable[bytes]):
    """
        Read a set of headers.
        Stop once a blank line is reached.

        Returns:
            A headers object

        Raises:
            exceptions.HttpSyntaxException
    """
    ret = []
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
                raise ValueError(f"Invalid header line: {line}")
    return headers.Headers(ret)


def read_request_head(lines: List[bytes]) -> request.Request:
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

    return request.Request(
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


def read_response_head(lines: List[bytes]) -> response.Response:
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

    return response.Response(
        http_version=http_version,
        status_code=status_code,
        reason=reason,
        headers=headers,
        content=None,
        trailers=None,
        timestamp_start=time.time(),
        timestamp_end=None,
    )


def expected_http_body_size(
        request: request.Request,
        response: Optional[response.Response] = None,
        expect_continue_as_0: bool = True,
):
    """
    Like the non-sans-io version, but also treating CONNECT as content-length: 0
    """
    if request.data.method.upper() == b"CONNECT":
        return 0
    return read.expected_http_body_size(request, response, expect_continue_as_0)
