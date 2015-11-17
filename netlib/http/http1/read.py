from __future__ import absolute_import, print_function, division
import time
import sys
import re

from ... import utils
from ...exceptions import HttpReadDisconnect, HttpSyntaxException, HttpException, TcpDisconnect
from .. import Request, Response, Headers


def read_request(rfile, body_size_limit=None):
    request = read_request_head(rfile)
    expected_body_size = expected_http_body_size(request)
    request.data.content = b"".join(read_body(rfile, expected_body_size, limit=body_size_limit))
    request.timestamp_end = time.time()
    return request


def read_request_head(rfile):
    """
    Parse an HTTP request head (request line + headers) from an input stream

    Args:
        rfile: The input stream

    Returns:
        The HTTP request object (without body)

    Raises:
        HttpReadDisconnect: No bytes can be read from rfile.
        HttpSyntaxException: The input is malformed HTTP.
        HttpException: Any other error occured.
    """
    timestamp_start = time.time()
    if hasattr(rfile, "reset_timestamps"):
        rfile.reset_timestamps()

    form, method, scheme, host, port, path, http_version = _read_request_line(rfile)
    headers = _read_headers(rfile)

    if hasattr(rfile, "first_byte_timestamp"):
        # more accurate timestamp_start
        timestamp_start = rfile.first_byte_timestamp

    return Request(
        form, method, scheme, host, port, path, http_version, headers, None, timestamp_start
    )


def read_response(rfile, request, body_size_limit=None):
    response = read_response_head(rfile)
    expected_body_size = expected_http_body_size(request, response)
    response.data.content = b"".join(read_body(rfile, expected_body_size, body_size_limit))
    response.timestamp_end = time.time()
    return response


def read_response_head(rfile):
    """
    Parse an HTTP response head (response line + headers) from an input stream

    Args:
        rfile: The input stream

    Returns:
        The HTTP request object (without body)

    Raises:
        HttpReadDisconnect: No bytes can be read from rfile.
        HttpSyntaxException: The input is malformed HTTP.
        HttpException: Any other error occured.
    """

    timestamp_start = time.time()
    if hasattr(rfile, "reset_timestamps"):
        rfile.reset_timestamps()

    http_version, status_code, message = _read_response_line(rfile)
    headers = _read_headers(rfile)

    if hasattr(rfile, "first_byte_timestamp"):
        # more accurate timestamp_start
        timestamp_start = rfile.first_byte_timestamp

    return Response(http_version, status_code, message, headers, None, timestamp_start)


def read_body(rfile, expected_size, limit=None, max_chunk_size=4096):
    """
        Read an HTTP message body

        Args:
            rfile: The input stream
            expected_size: The expected body size (see :py:meth:`expected_body_size`)
            limit: Maximum body size
            max_chunk_size: Maximium chunk size that gets yielded

        Returns:
            A generator that yields byte chunks of the content.

        Raises:
            HttpException, if an error occurs

        Caveats:
            max_chunk_size is not considered if the transfer encoding is chunked.
    """
    if not limit or limit < 0:
        limit = sys.maxsize
    if not max_chunk_size:
        max_chunk_size = limit

    if expected_size is None:
        for x in _read_chunked(rfile, limit):
            yield x
    elif expected_size >= 0:
        if limit is not None and expected_size > limit:
            raise HttpException(
                "HTTP Body too large. "
                "Limit is {}, content length was advertised as {}".format(limit, expected_size)
            )
        bytes_left = expected_size
        while bytes_left:
            chunk_size = min(bytes_left, max_chunk_size)
            content = rfile.read(chunk_size)
            if len(content) < chunk_size:
                raise HttpException("Unexpected EOF")
            yield content
            bytes_left -= chunk_size
    else:
        bytes_left = limit
        while bytes_left:
            chunk_size = min(bytes_left, max_chunk_size)
            content = rfile.read(chunk_size)
            if not content:
                return
            yield content
            bytes_left -= chunk_size
        not_done = rfile.read(1)
        if not_done:
            raise HttpException("HTTP body too large. Limit is {}.".format(limit))


def connection_close(http_version, headers):
    """
        Checks the message to see if the client connection should be closed
        according to RFC 2616 Section 8.1.
    """
    # At first, check if we have an explicit Connection header.
    if "connection" in headers:
        tokens = utils.get_header_tokens(headers, "connection")
        if "close" in tokens:
            return True
        elif "keep-alive" in tokens:
            return False

    # If we don't have a Connection header, HTTP 1.1 connections are assumed to
    # be persistent
    return http_version != "HTTP/1.1" and http_version != b"HTTP/1.1"  # FIXME: Remove one case.


def expected_http_body_size(request, response=None):
    """
        Returns:
            The expected body length:
            - a positive integer, if the size is known in advance
            - None, if the size in unknown in advance (chunked encoding)
            - -1, if all data should be read until end of stream.

        Raises:
            HttpSyntaxException, if the content length header is invalid
    """
    # Determine response size according to
    # http://tools.ietf.org/html/rfc7230#section-3.3
    if not response:
        headers = request.headers
        response_code = None
        is_request = True
    else:
        headers = response.headers
        response_code = response.status_code
        is_request = False

    if is_request:
        if headers.get("expect", "").lower() == "100-continue":
            return 0
    else:
        if request.method.upper() == "HEAD":
            return 0
        if 100 <= response_code <= 199:
            return 0
        if response_code == 200 and request.method.upper() == "CONNECT":
            return 0
        if response_code in (204, 304):
            return 0

    if "chunked" in headers.get("transfer-encoding", "").lower():
        return None
    if "content-length" in headers:
        try:
            size = int(headers["content-length"])
            if size < 0:
                raise ValueError()
            return size
        except ValueError:
            raise HttpSyntaxException("Unparseable Content Length")
    if is_request:
        return 0
    return -1


def _get_first_line(rfile):
    try:
        line = rfile.readline()
        if line == b"\r\n" or line == b"\n":
            # Possible leftover from previous message
            line = rfile.readline()
    except TcpDisconnect:
        raise HttpReadDisconnect("Remote disconnected")
    if not line:
        raise HttpReadDisconnect("Remote disconnected")
    return line.strip()


def _read_request_line(rfile):
    try:
        line = _get_first_line(rfile)
    except HttpReadDisconnect:
        # We want to provide a better error message.
        raise HttpReadDisconnect("Client disconnected")

    try:
        method, path, http_version = line.split(b" ")

        if path == b"*" or path.startswith(b"/"):
            form = "relative"
            scheme, host, port = None, None, None
        elif method == b"CONNECT":
            form = "authority"
            host, port = _parse_authority_form(path)
            scheme, path = None, None
        else:
            form = "absolute"
            scheme, host, port, path = utils.parse_url(path)

        _check_http_version(http_version)
    except ValueError:
        raise HttpSyntaxException("Bad HTTP request line: {}".format(line))

    return form, method, scheme, host, port, path, http_version


def _parse_authority_form(hostport):
    """
        Returns (host, port) if hostport is a valid authority-form host specification.
        http://tools.ietf.org/html/draft-luotonen-web-proxy-tunneling-01 section 3.1

        Raises:
            ValueError, if the input is malformed
    """
    try:
        host, port = hostport.split(b":")
        port = int(port)
        if not utils.is_valid_host(host) or not utils.is_valid_port(port):
            raise ValueError()
    except ValueError:
        raise HttpSyntaxException("Invalid host specification: {}".format(hostport))

    return host, port


def _read_response_line(rfile):
    try:
        line = _get_first_line(rfile)
    except HttpReadDisconnect:
        # We want to provide a better error message.
        raise HttpReadDisconnect("Server disconnected")

    try:

        parts = line.split(b" ", 2)
        if len(parts) == 2:  # handle missing message gracefully
            parts.append(b"")

        http_version, status_code, message = parts
        status_code = int(status_code)
        _check_http_version(http_version)

    except ValueError:
        raise HttpSyntaxException("Bad HTTP response line: {}".format(line))

    return http_version, status_code, message


def _check_http_version(http_version):
    if not re.match(br"^HTTP/\d\.\d$", http_version):
        raise HttpSyntaxException("Unknown HTTP version: {}".format(http_version))


def _read_headers(rfile):
    """
        Read a set of headers.
        Stop once a blank line is reached.

        Returns:
            A headers object

        Raises:
            HttpSyntaxException
    """
    ret = []
    while True:
        line = rfile.readline()
        if not line or line == b"\r\n" or line == b"\n":
            break
        if line[0] in b" \t":
            if not ret:
                raise HttpSyntaxException("Invalid headers")
            # continued header
            ret[-1][1] = ret[-1][1] + b'\r\n ' + line.strip()
        else:
            try:
                name, value = line.split(b":", 1)
                value = value.strip()
                if not name:
                    raise ValueError()
                ret.append([name, value])
            except ValueError:
                raise HttpSyntaxException("Invalid headers")
    return Headers(ret)


def _read_chunked(rfile, limit=sys.maxsize):
    """
    Read a HTTP body with chunked transfer encoding.

    Args:
        rfile: the input file
        limit: A positive integer
    """
    total = 0
    while True:
        line = rfile.readline(128)
        if line == b"":
            raise HttpException("Connection closed prematurely")
        if line != b"\r\n" and line != b"\n":
            try:
                length = int(line, 16)
            except ValueError:
                raise HttpSyntaxException("Invalid chunked encoding length: {}".format(line))
            total += length
            if total > limit:
                raise HttpException(
                    "HTTP Body too large. Limit is {}, "
                    "chunked content longer than {}".format(limit, total)
                )
            chunk = rfile.read(length)
            suffix = rfile.readline(5)
            if suffix != b"\r\n":
                raise HttpSyntaxException("Malformed chunked body")
            if length == 0:
                return
            yield chunk
