from mitmproxy import dns
from mitmproxy import http


def tdnsreq(**kwargs) -> dns.Message:
    """
    Returns:
        mitmproxy.dns.Message
    """
    default = dict(
        timestamp=946681200,
        id=42,
        query=True,
        op_code=dns.op_codes.QUERY,
        authoritative_answer=False,
        truncation=False,
        recursion_desired=True,
        recursion_available=False,
        reserved=0,
        response_code=dns.response_codes.NOERROR,
        questions=[dns.Question("dns.google", dns.types.A, dns.classes.IN)],
        answers=[],
        authorities=[],
        additionals=[],
    )
    default.update(kwargs)
    return dns.Message(**default)  # type: ignore


def tdnsresp(**kwargs) -> dns.Message:
    """
    Returns:
        mitmproxy.dns.Message
    """
    default = dict(
        timestamp=946681201,
        id=42,
        query=False,
        op_code=dns.op_codes.QUERY,
        authoritative_answer=False,
        truncation=False,
        recursion_desired=True,
        recursion_available=True,
        reserved=0,
        response_code=dns.response_codes.NOERROR,
        questions=[dns.Question("dns.google", dns.types.A, dns.classes.IN)],
        answers=[
            dns.ResourceRecord(
                "dns.google", dns.types.A, dns.classes.IN, 32, b"\x08\x08\x08\x08"
            ),
            dns.ResourceRecord(
                "dns.google", dns.types.A, dns.classes.IN, 32, b"\x08\x08\x04\x04"
            ),
        ],
        authorities=[],
        additionals=[],
    )
    default.update(kwargs)
    return dns.Message(**default)  # type: ignore


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
        headers=http.Headers(
            ((b"header-response", b"svalue"), (b"content-length", b"7"))
        ),
        content=b"message",
        trailers=None,
        timestamp_start=946681202,
        timestamp_end=946681203,
    )
    default.update(kwargs)
    return http.Response(**default)  # type: ignore
