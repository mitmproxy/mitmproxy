import string, urlparse, binascii
import odict, utils

class HttpError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "HttpError(%s, %s)"%(self.code, self.msg)


class HttpErrorConnClosed(HttpError): pass


def _is_valid_port(port):
    if not 0 <= port <= 65535:
        return False
    return True


def _is_valid_host(host):
    try:
        host.decode("idna")
    except ValueError:
        return False
    if "\0" in host:
        return None
    return True


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.

        Checks that:
            port is an integer 0-65535
            host is a valid IDNA-encoded hostname with no null-bytes
            path is valid ASCII
    """
    try:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    except ValueError:
        return None
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
    if not _is_valid_host(host):
        return None
    if not utils.isascii(path):
        return None
    if not _is_valid_port(port):
        return None
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


def read_chunked(fp, headers, limit, is_request):
    """
        Read a chunked HTTP body.

        May raise HttpError.
    """
    # FIXME: Should check if chunked is the final encoding in the headers
    # http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-16#section-3.3 3.3 2.
    content = ""
    total = 0
    code = 400 if is_request else 502
    while 1:
        line = fp.readline(128)
        if line == "":
            raise HttpErrorConnClosed(code, "Connection closed prematurely")
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
            raise HttpErrorConnClosed(code, "Connection closed prematurely")
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


def parse_http_basic_auth(s):
    words = s.split()
    if len(words) != 2:
        return None
    scheme = words[0]
    try:
        user = binascii.a2b_base64(words[1])
    except binascii.Error:
        return None
    parts = user.split(':')
    if len(parts) != 2:
        return None
    return scheme, parts[0], parts[1]


def assemble_http_basic_auth(scheme, username, password):
    v = binascii.b2a_base64(username + ":" + password)
    return scheme + " " + v


def parse_init(line):
    try:
        method, url, protocol = string.split(line)
    except ValueError:
        return None
    httpversion = parse_http_protocol(protocol)
    if not httpversion:
        return None
    if not utils.isascii(method):
        return None
    return method, url, httpversion


def parse_init_connect(line):
    """
        Returns (host, port, httpversion) if line is a valid CONNECT line.
        http://tools.ietf.org/html/draft-luotonen-web-proxy-tunneling-01 section 3.1
    """
    v = parse_init(line)
    if not v:
        return None
    method, url, httpversion = v

    if method.upper() != 'CONNECT':
        return None
    try:
        host, port = url.split(":")
    except ValueError:
        return None
    try:
        port = int(port)
    except ValueError:
        return None
    if not _is_valid_port(port):
        return None
    if not _is_valid_host(host):
        return None
    return host, port, httpversion


def parse_init_proxy(line):
    v = parse_init(line)
    if not v:
        return None
    method, url, httpversion = v

    parts = parse_url(url)
    if not parts:
        return None
    scheme, host, port, path = parts
    return method, scheme, host, port, path, httpversion


def parse_init_http(line):
    """
        Returns (method, url, httpversion)
    """
    v = parse_init(line)
    if not v:
        return None
    method, url, httpversion = v
    if not utils.isascii(url):
        return None
    if not (url.startswith("/") or url == "*"):
        return None
    return method, url, httpversion


def connection_close(httpversion, headers):
    """
        Checks the message to see if the client connection should be closed according to RFC 2616 Section 8.1
    """
    # At first, check if we have an explicit Connection header.
    if "connection" in headers:
        toks = get_header_tokens(headers, "connection")
        if "close" in toks:
            return True
        elif "keep-alive" in toks:
            return False
    # If we don't have a Connection header, HTTP 1.1 connections are assumed to be persistent
    if httpversion == (1, 1):
        return False
    return True


def parse_response_line(line):
    parts = line.strip().split(" ", 2)
    if len(parts) == 2: # handle missing message gracefully
        parts.append("")
    if len(parts) != 3:
        return None
    proto, code, msg = parts
    try:
        code = int(code)
    except ValueError:
        return None
    return (proto, code, msg)


def read_response(rfile, method, body_size_limit):
    """
        Return an (httpversion, code, msg, headers, content) tuple.
    """
    line = rfile.readline()
    if line == "\r\n" or line == "\n": # Possible leftover from previous message
        line = rfile.readline()
    if not line:
        raise HttpErrorConnClosed(502, "Server disconnect.")
    parts = parse_response_line(line)
    if not parts:
        raise HttpError(502, "Invalid server response: %s"%repr(line))
    proto, code, msg = parts
    httpversion = parse_http_protocol(proto)
    if httpversion is None:
        raise HttpError(502, "Invalid HTTP version in line: %s"%repr(proto))
    headers = read_headers(rfile)
    if headers is None:
        raise HttpError(502, "Invalid headers.")

    # Parse response body according to http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-16#section-3.3
    if method in ["HEAD", "CONNECT"] or (code in [204, 304]) or 100 <= code <= 199:
        content = ""
    else:
        content = read_http_body(rfile, headers, body_size_limit, False)
    return httpversion, code, msg, headers, content


def read_http_body(rfile, headers, limit, is_request):
    """
        Read an HTTP message body:

            rfile: A file descriptor to read from
            headers: An ODictCaseless object
            limit: Size limit.
            is_request: True if the body to read belongs to a request, False otherwise
    """
    if has_chunked_encoding(headers):
        content = read_chunked(rfile, headers, limit, is_request)
    elif "content-length" in headers:
        try:
            l = int(headers["content-length"][0])
            if l < 0:
                raise ValueError()
        except ValueError:
            raise HttpError(400 if is_request else 502, "Invalid content-length header: %s"%headers["content-length"])
        if limit is not None and l > limit:
            raise HttpError(400 if is_request else 509, "HTTP Body too large. Limit is %s, content-length was %s"%(limit, l))
        content = rfile.read(l)
    elif is_request:
        content = ""
    else:
        content = rfile.read(limit if limit else -1)
        not_done = rfile.read(1)
        if not_done:
            raise HttpError(400 if is_request else 509, "HTTP Body too large. Limit is %s," % limit)
    return content