from __future__ import absolute_import, print_function, division

from ... import utils
import itertools
from ...exceptions import HttpException
from .. import CONTENT_MISSING


def assemble_request(request):
    if request.body == CONTENT_MISSING:
        raise HttpException("Cannot assemble flow with CONTENT_MISSING")
    head = assemble_request_head(request)
    body = b"".join(assemble_body(request.headers, [request.body]))
    return head + body


def assemble_request_head(request):
    first_line = _assemble_request_line(request)
    headers = _assemble_request_headers(request)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_response(response):
    if response.body == CONTENT_MISSING:
        raise HttpException("Cannot assemble flow with CONTENT_MISSING")
    head = assemble_response_head(response)
    body = b"".join(assemble_body(response.headers, [response.body]))
    return head + body


def assemble_response_head(response):
    first_line = _assemble_response_line(response)
    headers = _assemble_response_headers(response)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_body(headers, body_chunks):
    if b"chunked" in headers.get(b"transfer-encoding", b"").lower():
        for chunk in body_chunks:
            if chunk:
                yield b"%x\r\n%s\r\n" % (len(chunk), chunk)
        yield b"0\r\n\r\n"
    else:
        for chunk in body_chunks:
            yield chunk


def _assemble_request_line(request, form=None):
    if form is None:
        form = request.form_out
    if form == "relative":
        return b"%s %s %s" % (
            request.method,
            request.path,
            request.http_version
        )
    elif form == "authority":
        return b"%s %s:%d %s" % (
            request.method,
            request.host,
            request.port,
            request.http_version
        )
    elif form == "absolute":
        return b"%s %s://%s:%d%s %s" % (
            request.method,
            request.scheme,
            request.host,
            request.port,
            request.path,
            request.http_version
        )
    else:  # pragma: nocover
        raise RuntimeError("Invalid request form")


def _assemble_request_headers(request):
    headers = request.headers.copy()
    if b"host" not in headers and request.scheme and request.host and request.port:
        headers[b"Host"] = utils.hostport(
            request.scheme,
            request.host,
            request.port
        )
    return bytes(headers)


def _assemble_response_line(response):
    return b"%s %d %s" % (
        response.http_version,
        response.status_code,
        response.msg,
    )


def _assemble_response_headers(response):
    return bytes(response.headers)
