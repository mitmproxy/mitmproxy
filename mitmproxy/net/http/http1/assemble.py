import mitmproxy.net.http.url
from mitmproxy import exceptions


def assemble_request(request):
    if request.data.content is None:
        raise exceptions.HttpException("Cannot assemble flow with missing content")
    head = assemble_request_head(request)
    body = b"".join(assemble_body(request.data.headers, [request.data.content]))
    return head + body


def assemble_request_head(request):
    first_line = _assemble_request_line(request.data)
    headers = _assemble_request_headers(request.data)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_response(response):
    if response.data.content is None:
        raise exceptions.HttpException("Cannot assemble flow with missing content")
    head = assemble_response_head(response)
    body = b"".join(assemble_body(response.data.headers, [response.data.content]))
    return head + body


def assemble_response_head(response):
    first_line = _assemble_response_line(response.data)
    headers = _assemble_response_headers(response.data)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_body(headers, body_chunks):
    if "chunked" in headers.get("transfer-encoding", "").lower():
        for chunk in body_chunks:
            if chunk:
                yield b"%x\r\n%s\r\n" % (len(chunk), chunk)
        yield b"0\r\n\r\n"
    else:
        for chunk in body_chunks:
            yield chunk


def _assemble_request_line(request_data):
    """
    Args:
        request_data (mitmproxy.net.http.request.RequestData)
    """
    form = request_data.first_line_format
    if form == "relative":
        return b"%s %s %s" % (
            request_data.method,
            request_data.path,
            request_data.http_version
        )
    elif form == "authority":
        return b"%s %s:%d %s" % (
            request_data.method,
            request_data.host,
            request_data.port,
            request_data.http_version
        )
    elif form == "absolute":
        return b"%s %s://%s:%d%s %s" % (
            request_data.method,
            request_data.scheme,
            request_data.host,
            request_data.port,
            request_data.path,
            request_data.http_version
        )
    else:
        raise RuntimeError("Invalid request form")


def _assemble_request_headers(request_data):
    """
    Args:
        request_data (mitmproxy.net.http.request.RequestData)
    """
    headers = request_data.headers
    if "host" not in headers and request_data.scheme and request_data.host and request_data.port:
        headers = headers.copy()
        headers["host"] = mitmproxy.net.http.url.hostport(
            request_data.scheme,
            request_data.host,
            request_data.port
        )
    return bytes(headers)


def _assemble_response_line(response_data):
    return b"%s %d %s" % (
        response_data.http_version,
        response_data.status_code,
        response_data.reason,
    )


def _assemble_response_headers(response):
    return bytes(response.headers)
