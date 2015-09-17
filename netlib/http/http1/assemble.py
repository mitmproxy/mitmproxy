from __future__ import absolute_import, print_function, division

from ... import utils
from ...exceptions import HttpException
from .. import CONTENT_MISSING


def assemble_request(request):
    if request.body == CONTENT_MISSING:
        raise HttpException("Cannot assemble flow with CONTENT_MISSING")
    head = assemble_request_head(request)
    return head + request.body


def assemble_request_head(request):
    first_line = _assemble_request_line(request)
    headers = _assemble_request_headers(request)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_response(response):
    if response.body == CONTENT_MISSING:
        raise HttpException("Cannot assemble flow with CONTENT_MISSING")
    head = assemble_response_head(response)
    return head + response.body


def assemble_response_head(response, preserve_transfer_encoding=False):
    first_line = _assemble_response_line(response)
    headers = _assemble_response_headers(response, preserve_transfer_encoding)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def _assemble_request_line(request, form=None):
    if form is None:
        form = request.form_out
    if form == "relative":
        return b"%s %s %s" % (
            request.method,
            request.path,
            request.httpversion
        )
    elif form == "authority":
        return b"%s %s:%d %s" % (
            request.method,
            request.host,
            request.port,
            request.httpversion
        )
    elif form == "absolute":
        return b"%s %s://%s:%d%s %s" % (
            request.method,
            request.scheme,
            request.host,
            request.port,
            request.path,
            request.httpversion
        )
    else:  # pragma: nocover
        raise RuntimeError("Invalid request form")


def _assemble_request_headers(request):
    headers = request.headers.copy()
    for k in request._headers_to_strip_off:
        headers.pop(k, None)
    if b"host" not in headers and request.scheme and request.host and request.port:
        headers[b"Host"] = utils.hostport(
            request.scheme,
            request.host,
            request.port
        )

    # If content is defined (i.e. not None or CONTENT_MISSING), we always
    # add a content-length header.
    if request.body or request.body == b"":
        headers[b"Content-Length"] = str(len(request.body)).encode("ascii")

    return bytes(headers)


def _assemble_response_line(response):
    return b"%s %d %s" % (
        response.httpversion,
        response.status_code,
        response.msg,
    )


def _assemble_response_headers(response, preserve_transfer_encoding=False):
    # TODO: Remove preserve_transfer_encoding
    headers = response.headers.copy()
    for k in response._headers_to_strip_off:
        headers.pop(k, None)
    if not preserve_transfer_encoding:
        headers.pop(b"Transfer-Encoding", None)

        # If body is defined (i.e. not None or CONTENT_MISSING),
        # we now need to set a content-length header.
        if response.body or response.body == b"":
            headers[b"Content-Length"] = str(len(response.body)).encode("ascii")

    return bytes(headers)
