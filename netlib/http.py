import string, urlparse
import odict

class HttpError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "HttpError(%s, %s)"%(self.code, self.msg)


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.
    """
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    if not scheme:
        return None
    if ':' in netloc:
        host, port = string.rsplit(netloc, ':', maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    return scheme, host, port, path


def read_headers(fp):
    """
        Read a set of headers from a file pointer. Stop once a blank line is
        reached. Return a ODictCaseless object, or None if headers are invalid.
    """
    ret = []
    name = ''
    while 1:
        line = fp.readline()
        if not line or line == '\r\n' or line == '\n':
            break
        if line[0] in ' \t':
            if not ret:
                return None
            # continued header
            ret[-1][1] = ret[-1][1] + '\r\n ' + line.strip()
        else:
            i = line.find(':')
            # We're being liberal in what we accept, here.
            if i > 0:
                name = line[:i]
                value = line[i+1:].strip()
                ret.append([name, value])
            else:
                return None
    return odict.ODictCaseless(ret)


def read_chunked(code, fp, limit):
    """
        Read a chunked HTTP body.

        May raise HttpError.
    """
    content = ""
    total = 0
    while 1:
        line = fp.readline(128)
        if line == "":
            raise HttpError(code, "Connection closed prematurely")
        if line != '\r\n' and line != '\n':
            try:
                length = int(line, 16)
            except ValueError:
                # FIXME: Not strictly correct - this could be from the server, in which
                # case we should send a 502.
                raise HttpError(code, "Invalid chunked encoding length: %s"%line)
            if not length:
                break
            total += length
            if limit is not None and total > limit:
                msg = "HTTP Body too large."\
                      " Limit is %s, chunked content length was at least %s"%(limit, total)
                raise HttpError(code, msg)
            content += fp.read(length)
            line = fp.readline(5)
            if line != '\r\n':
                raise HttpError(code, "Malformed chunked body")
    while 1:
        line = fp.readline()
        if line == "":
            raise HttpError(code, "Connection closed prematurely")
        if line == '\r\n' or line == '\n':
            break
    return content


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    toks = []
    for i in headers[key]:
        for j in i.split(","):
            toks.append(j.strip())
    return toks


def has_chunked_encoding(headers):
    return "chunked" in [i.lower() for i in get_header_tokens(headers, "transfer-encoding")]


def read_http_body(code, rfile, headers, all, limit):
    """
        Read an HTTP body:

            code: The HTTP error code to be used when raising HttpError
            rfile: A file descriptor to read from
            headers: An ODictCaseless object
            all: Should we read all data?
            limit: Size limit.
    """
    if has_chunked_encoding(headers):
        content = read_chunked(code, rfile, limit)
    elif "content-length" in headers:
        try:
            l = int(headers["content-length"][0])
        except ValueError:
            # FIXME: Not strictly correct - this could be from the server, in which
            # case we should send a 502.
            raise HttpError(code, "Invalid content-length header: %s"%headers["content-length"])
        if limit is not None and l > limit:
            raise HttpError(code, "HTTP Body too large. Limit is %s, content-length was %s"%(limit, l))
        content = rfile.read(l)
    elif all:
        content = rfile.read(limit if limit else -1)
    else:
        content = ""
    return content


def parse_http_protocol(s):
    """
        Parse an HTTP protocol declaration. Returns a (major, minor) tuple, or
        None.
    """
    if not s.startswith("HTTP/"):
        return None
    _, version = s.split('/', 1)
    if "." not in version:
        return None
    major, minor = version.split('.', 1)
    try:
        major = int(major)
        minor = int(minor)
    except ValueError:
        return None
    return major, minor


def parse_init_connect(line):
    try:
        method, url, protocol = string.split(line)
    except ValueError:
        return None
    if method != 'CONNECT':
        return None
    try:
        host, port = url.split(":")
    except ValueError:
        return None
    port = int(port)
    httpversion = parse_http_protocol(protocol)
    if not httpversion:
        return None
    return host, port, httpversion


def parse_init_proxy(line):
    try:
        method, url, protocol = string.split(line)
    except ValueError:
        return None
    parts = parse_url(url)
    if not parts:
        return None
    scheme, host, port, path = parts
    httpversion = parse_http_protocol(protocol)
    if not httpversion:
        return None
    return method, scheme, host, port, path, httpversion


def parse_init_http(line):
    """
        Returns (method, url, httpversion)
    """
    try:
        method, url, protocol = string.split(line)
    except ValueError:
        return None
    if not (url.startswith("/") or url == "*"):
        return None
    httpversion = parse_http_protocol(protocol)
    if not httpversion:
        return None
    return method, url, httpversion


def request_connection_close(httpversion, headers):
    """
        Checks the request to see if the client connection should be closed.
    """
    if "connection" in headers:
        toks = get_header_tokens(headers, "connection")
        if "close" in toks:
            return True
        elif "keep-alive" in toks:
            return False
    # HTTP 1.1 connections are assumed to be persistent
    if httpversion == (1, 1):
        return False
    return True


def response_connection_close(httpversion, headers):
    """
        Checks the response to see if the client connection should be closed.
    """
    if request_connection_close(httpversion, headers):
        return True
    elif (not has_chunked_encoding(headers)) and "content-length" in headers:
        return False
    return True


def read_http_body_request(rfile, wfile, headers, httpversion, limit):
    """
        Read the HTTP body from a client request.
    """
    if "expect" in headers:
        # FIXME: Should be forwarded upstream
        if "100-continue" in headers['expect'] and httpversion >= (1, 1):
            wfile.write('HTTP/1.1 100 Continue\r\n')
            wfile.write('\r\n')
            del headers['expect']
    return read_http_body(400, rfile, headers, False, limit)


def read_http_body_response(rfile, headers, limit):
    """
        Read the HTTP body from a server response.
    """
    all = "close" in get_header_tokens(headers, "connection")
    return read_http_body(500, rfile, headers, all, limit)


def read_response(rfile, method, body_size_limit):
    """
        Return an (httpversion, code, msg, headers, content) tuple.
    """
    line = rfile.readline()
    if line == "\r\n" or line == "\n": # Possible leftover from previous message
        line = rfile.readline()
    if not line:
        raise HttpError(502, "Blank server response.")
    parts = line.strip().split(" ", 2)
    if len(parts) == 2: # handle missing message gracefully
        parts.append("")
    if not len(parts) == 3:
        raise HttpError(502, "Invalid server response: %s"%repr(line))
    proto, code, msg = parts
    httpversion = parse_http_protocol(proto)
    if httpversion is None:
        raise HttpError(502, "Invalid HTTP version in line: %s"%repr(proto))
    try:
        code = int(code)
    except ValueError:
        raise HttpError(502, "Invalid server response: %s"%repr(line))
    headers = read_headers(rfile)
    if headers is None:
        raise HttpError(502, "Invalid headers.")
    if code >= 100 and code <= 199:
        return read_response(rfile, method, body_size_limit)
    if method == "HEAD" or code == 204 or code == 304:
        content = ""
    else:
        content = read_http_body_response(rfile, headers, body_size_limit)
    return httpversion, code, msg, headers, content
