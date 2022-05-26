def assemble_request(request):
    if request.data.content is None:
        raise ValueError("Cannot assemble flow with missing content")
    head = assemble_request_head(request)
    body = b"".join(
        assemble_body(
            request.data.headers, [request.data.content], request.data.trailers
        )
    )
    return head + body


def assemble_request_head(request):
    first_line = _assemble_request_line(request.data)
    headers = _assemble_request_headers(request.data)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_response(response):
    if response.data.content is None:
        raise ValueError("Cannot assemble flow with missing content")
    head = assemble_response_head(response)
    body = b"".join(
        assemble_body(
            response.data.headers, [response.data.content], response.data.trailers
        )
    )
    return head + body


def assemble_response_head(response):
    first_line = _assemble_response_line(response.data)
    headers = _assemble_response_headers(response.data)
    return b"%s\r\n%s\r\n" % (first_line, headers)


def assemble_body(headers, body_chunks, trailers):
    if "chunked" in headers.get("transfer-encoding", "").lower():
        for chunk in body_chunks:
            if chunk:
                yield b"%x\r\n%s\r\n" % (len(chunk), chunk)
        if trailers:
            yield b"0\r\n%s\r\n" % trailers
        else:
            yield b"0\r\n\r\n"
    else:
        if trailers:
            raise ValueError(
                "Sending HTTP/1.1 trailer headers requires transfer-encoding: chunked"
            )
        for chunk in body_chunks:
            yield chunk


def _assemble_request_line(request_data):
    """
    Args:
        request_data (mitmproxy.net.http.request.RequestData)
    """
    if request_data.method.upper() == b"CONNECT":
        return b"%s %s %s" % (
            request_data.method,
            request_data.authority,
            request_data.http_version,
        )
    elif request_data.authority:
        return b"%s %s://%s%s %s" % (
            request_data.method,
            request_data.scheme,
            request_data.authority,
            request_data.path,
            request_data.http_version,
        )
    else:
        return b"%s %s %s" % (
            request_data.method,
            request_data.path,
            request_data.http_version,
        )


def _assemble_request_headers(request_data):
    """
    Args:
        request_data (mitmproxy.net.http.request.RequestData)
    """
    return bytes(request_data.headers)


def _assemble_response_line(response_data):
    return b"%s %d %s" % (
        response_data.http_version,
        response_data.status_code,
        response_data.reason,
    )


def _assemble_response_headers(response):
    return bytes(response.headers)
