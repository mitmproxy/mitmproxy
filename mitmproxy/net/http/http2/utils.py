from mitmproxy.net.http import url


def parse_headers(headers):
    authority = headers.get(':authority', '').encode()
    method = headers.get(':method', 'GET').encode()
    scheme = headers.get(':scheme', 'https').encode()
    path = headers.get(':path', '/').encode()

    headers.pop(":method", None)
    headers.pop(":scheme", None)
    headers.pop(":path", None)

    host = None
    port = None

    if method == b'CONNECT':
        raise NotImplementedError("CONNECT over HTTP/2 is not implemented.")

    if path == b'*' or path.startswith(b"/"):
        first_line_format = "relative"
    else:
        first_line_format = "absolute"
        scheme, host, port, _ = url.parse(path)

    if authority:
        host, _, port = authority.partition(b':')

    if not host:
        host = b'localhost'

    if not port:
        port = 443 if scheme == b'https' else 80

    port = int(port)

    return first_line_format, method, scheme, host, port, path
