from mitmproxy import http


def treq(**kwargs) -> http.Request:
    """
    Returns:
        mitmproxy.net.http.Request
    """
    default = dict(
        host="address",
        port=22,
        method=b"GET",
        scheme=b"http",
        authority=b"",
        path=b"/path",
        http_version=b"HTTP/1.1",
        headers=http.Headers(((b"header", b"qvalue"), (b"content-length", b"7"))),
        content=b"content",
        trailers=None,
        timestamp_start=946681200,
        timestamp_end=946681201,
    )
    default.update(kwargs)
    return http.Request(**default)  # type: ignore


def tresp(**kwargs) -> http.Response:
    """
    Returns:
        mitmproxy.net.http.Response
    """
    default = dict(
        http_version=b"HTTP/1.1",
        status_code=200,
        reason=b"OK",
        headers=http.Headers(((b"header-response", b"svalue"), (b"content-length", b"7"))),
        content=b"message",
        trailers=None,
        timestamp_start=946681202,
        timestamp_end=946681203,
    )
    default.update(kwargs)
    return http.Response(**default)  # type: ignore
