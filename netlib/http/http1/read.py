from __future__ import absolute_import, print_function, division
import time
import sys
import re

from ... import utils
from ...exceptions import HttpReadDisconnect, HttpSyntaxException, HttpException
from .. import Request, Response, Headers

ALPN_PROTO_HTTP1 = 'http/1.1'


def read_request(rfile, body_size_limit=None):
    request = read_request_head(rfile)
    request.body = read_message_body(rfile, request, limit=body_size_limit)
    request.timestamp_end = time.time()
    return request


def read_request_head(rfile):
    """
    Parse an HTTP request head (request line + headers) from an input stream

    Args:
        rfile: The input stream
        body_size_limit (bool): Maximum body size

    Returns:
        The HTTP request object

    Raises:
        HttpReadDisconnect: If no bytes can be read from rfile.
        HttpSyntaxException: If the input is invalid.
        HttpException: A different error occured.
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
    response.body = read_message_body(rfile, request, response, body_size_limit)
    response.timestamp_end = time.time()
    return response


def read_response_head(rfile):
    timestamp_start = time.time()
    if hasattr(rfile, "reset_timestamps"):
        rfile.reset_timestamps()

    http_version, status_code, message = _read_response_line(rfile)
    headers = _read_headers(rfile)

    if hasattr(rfile, "first_byte_timestamp"):
        # more accurate timestamp_start
        timestamp_start = rfile.first_byte_timestamp

    return Response(
        http_version,
        status_code,
        message,
        headers,
        None,
        timestamp_start
    )


def read_message_body(*args, **kwargs):
    chunks = read_message_body_chunked(*args, **kwargs)
    return b"".join(chunks)


def read_message_body_chunked(rfile, request, response=None, limit=None, max_chunk_size=None):
    """
        Read an HTTP message body:

        Args:
            If a request body should be read, only request should be passed.
            If a response body should be read, both request and response should be passed.

        Raises:
            HttpException
    """
    if not response:
        headers = request.headers
        response_code = None
        is_request = True
    else:
        headers = response.headers
        response_code = response.status_code
        is_request = False

    if not limit or limit < 0:
        limit = sys.maxsize
    if not max_chunk_size:
        max_chunk_size = limit

    expected_size = expected_http_body_size(
        headers, is_request, request.method, response_code
    )

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
    if b"connection" in headers:
        toks = utils.get_header_tokens(headers, "connection")
        if b"close" in toks:
            return True
        elif b"keep-alive" in toks:
            return False

    # If we don't have a Connection header, HTTP 1.1 connections are assumed to
    # be persistent
    return http_version != (1, 1)


def expected_http_body_size(
        headers,
        is_request,
        request_method,
        response_code,
):
    """
        Returns the expected body length:
         - a positive integer, if the size is known in advance
         - None, if the size in unknown in advance (chunked encoding)
         - -1, if all data should be read until end of stream.

        Raises:
            HttpSyntaxException, if the content length header is invalid
    """
    # Determine response size according to
    # http://tools.ietf.org/html/rfc7230#section-3.3
    if request_method:
        request_method = request_method.upper()

    is_empty_response = (not is_request and (
        request_method == b"HEAD" or
        100 <= response_code <= 199 or
        (response_code == 200 and request_method == b"CONNECT") or
        response_code in (204, 304)
    ))

    if is_empty_response:
        return 0
    if is_request and headers.get(b"expect", b"").lower() == b"100-continue":
        return 0
    if b"chunked" in headers.get(b"transfer-encoding", b"").lower():
        return None
    if b"content-length" in headers:
        try:
            size = int(headers[b"content-length"])
            if size < 0:
                raise ValueError()
            return size
        except ValueError:
            raise HttpSyntaxException("Unparseable Content Length")
    if is_request:
        return 0
    return -1


def _get_first_line(rfile):
    line = rfile.readline()
    if line == b"\r\n" or line == b"\n":
        # Possible leftover from previous message
        line = rfile.readline()
    if not line:
        raise HttpReadDisconnect()
    return line


def _read_request_line(rfile):
    line = _get_first_line(rfile)

    try:
        method, path, http_version = line.strip().split(b" ")

        if path == b"*" or path.startswith(b"/"):
            form = "relative"
            path.decode("ascii")  # should not raise a ValueError
            scheme, host, port = None, None, None
        elif method == b"CONNECT":
            form = "authority"
            host, port = _parse_authority_form(path)
            scheme, path = None, None
        else:
            form = "absolute"
            scheme, host, port, path = utils.parse_url(path)

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
        raise ValueError("Invalid host specification: {}".format(hostport))

    return host, port


def _read_response_line(rfile):
    line = _get_first_line(rfile)

    try:

        parts = line.strip().split(b" ")
        if len(parts) == 2:  # handle missing message gracefully
            parts.append(b"")

        http_version, status_code, message = parts
        status_code = int(status_code)
        _check_http_version(http_version)

    except ValueError:
        raise HttpSyntaxException("Bad HTTP response line: {}".format(line))

    return http_version, status_code, message


def _check_http_version(http_version):
    if not re.match(rb"^HTTP/\d\.\d$", http_version):
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
                ret.append([name, value])
            except ValueError:
                raise HttpSyntaxException("Invalid headers")
    return Headers(ret)


def _read_chunked(rfile, limit):
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
