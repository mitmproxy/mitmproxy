import string
import flow, utils

class ProtocolError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProtocolError(%s, %s)"%(self.code, self.msg)


def read_headers(fp):
    """
        Read a set of headers from a file pointer. Stop once a blank line
        is reached. Return a ODictCaseless object.
    """
    ret = []
    name = ''
    while 1:
        line = fp.readline()
        if not line or line == '\r\n' or line == '\n':
            break
        if line[0] in ' \t':
            # continued header
            ret[-1][1] = ret[-1][1] + '\r\n ' + line.strip()
        else:
            i = line.find(':')
            # We're being liberal in what we accept, here.
            if i > 0:
                name = line[:i]
                value = line[i+1:].strip()
                ret.append([name, value])
    return flow.ODictCaseless(ret)


def read_chunked(fp, limit):
    content = ""
    total = 0
    while 1:
        line = fp.readline(128)
        if line == "":
            raise IOError("Connection closed")
        if line == '\r\n' or line == '\n':
            continue
        try:
            length = int(line,16)
        except ValueError:
            # FIXME: Not strictly correct - this could be from the server, in which
            # case we should send a 502.
            raise ProtocolError(400, "Invalid chunked encoding length: %s"%line)
        if not length:
            break
        total += length
        if limit is not None and total > limit:
            msg = "HTTP Body too large."\
                  " Limit is %s, chunked content length was at least %s"%(limit, total)
            raise ProtocolError(509, msg)
        content += fp.read(length)
        line = fp.readline(5)
        if line != '\r\n':
            raise IOError("Malformed chunked body")
    while 1:
        line = fp.readline()
        if line == "":
            raise IOError("Connection closed")
        if line == '\r\n' or line == '\n':
            break
    return content


def has_chunked_encoding(headers):
    for i in headers["transfer-encoding"]:
        for j in i.split(","):
            if j.lower() == "chunked":
                return True
    return False


def read_http_body(rfile, headers, all, limit):
    if has_chunked_encoding(headers):
        content = read_chunked(rfile, limit)
    elif "content-length" in headers:
        try:
            l = int(headers["content-length"][0])
        except ValueError:
            # FIXME: Not strictly correct - this could be from the server, in which
            # case we should send a 502.
            raise ProtocolError(400, "Invalid content-length header: %s"%headers["content-length"])
        if limit is not None and l > limit:
            raise ProtocolError(509, "HTTP Body too large. Limit is %s, content-length was %s"%(limit, l))
        content = rfile.read(l)
    elif all:
        content = rfile.read(limit if limit else None)
    else:
        content = ""
    return content


def parse_http_protocol(s):
    if not s.startswith("HTTP/"):
        return None
    major, minor = s.split('/')[1].split('.')
    major = int(major)
    minor = int(minor)
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
    parts = utils.parse_url(url)
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
        for value in ",".join(headers['connection']).split(","):
            value = value.strip()
            if value == "close":
                return True
            elif value == "keep-alive":
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
    elif not has_chunked_encoding(headers) and "content-length" in headers:
        return True
    return False


def read_http_body_request(rfile, wfile, headers, httpversion, limit):
    if "expect" in headers:
        # FIXME: Should be forwarded upstream
        expect = ",".join(headers['expect'])
        if expect == "100-continue" and httpversion >= (1, 1):
            wfile.write('HTTP/1.1 100 Continue\r\n')
            wfile.write('Proxy-agent: %s\r\n'%version.NAMEVERSION)
            wfile.write('\r\n')
            del headers['expect']
    return read_http_body(rfile, headers, False, limit)


