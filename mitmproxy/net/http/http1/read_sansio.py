import re
from typing import Iterable, List, Optional, Tuple

from mitmproxy.net import check
from mitmproxy.net.http import headers, request, response, url


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


def _read_request_line(line: bytes) -> \
        Tuple[str, bytes, Optional[bytes], Optional[bytes], Optional[int], Optional[bytes], bytes]:
    try:
        method, path, http_version = line.split()
        if path == b"*" or path.startswith(b"/"):
            form = "relative"
            scheme, host, port = None, None, None
        elif method == b"CONNECT":
            form = "authority"
            host, port = _parse_authority_form(path)
            scheme, path = None, None
        else:
            form = "absolute"
            scheme, host, port, path = url.parse(path)

        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP request line: {line}") from e

    return form, method, scheme, host, port, path, http_version


def _read_response_line(line: bytes) -> Tuple[bytes, int, bytes]:
    try:
        parts = line.split(None, 2)
        if len(parts) == 2:  # handle missing message gracefully
            parts.append(b"")

        http_version, status_code, message = parts
        status_code = int(status_code)
        raise_if_http_version_unknown(http_version)
    except ValueError as e:
        raise ValueError(f"Bad HTTP response line: {line}") from e

    return http_version, status_code, message


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
    form, method, scheme, host, port, path, http_version = _read_request_line(lines[0])
    headers = _read_headers(lines[1:])

    return request.Request(
        form, method, scheme, host, port, path, http_version, headers
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
    http_version, status_code, message = _read_response_line(lines[0])
    headers = _read_headers(lines[1:])

    return response.Response(
        http_version, status_code, message, headers
    )
