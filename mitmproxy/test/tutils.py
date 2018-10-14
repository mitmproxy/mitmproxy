from io import BytesIO

from mitmproxy.net import tcp
from mitmproxy.net import http


def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = BytesIO(bytes)
    return tcp.Reader(fp)


def treq(**kwargs):
    """
    Returns:
        mitmproxy.net.http.Request
    """
    default = dict(
        first_line_format="relative",
        method=b"GET",
        scheme=b"http",
        host=b"address",
        port=22,
        path=b"/path",
        http_version=b"HTTP/1.1",
        headers=http.Headers(((b"header", b"qvalue"), (b"content-length", b"7"))),
        content=b"content",
        timestamp_start=946681200,
        timestamp_end=946681201,
    )
    default.update(kwargs)
    return http.Request(**default)


def tresp(**kwargs):
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
        timestamp_start=946681202,
        timestamp_end=946681203,
    )
    default.update(kwargs)
    return http.Response(**default)
