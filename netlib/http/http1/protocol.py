from __future__ import (absolute_import, print_function, division)
import binascii
import collections
import string
import sys
import urlparse

from netlib import odict, utils, tcp, http
from .. import status_codes
from ..exceptions import *

class HTTP1Protocol(object):

    # TODO: make this a regular class - just like Response
    Request = collections.namedtuple(
        "Request",
        [
            "form_in",
            "method",
            "scheme",
            "host",
            "port",
            "path",
            "httpversion",
            "headers",
            "content"
        ]
    )

    def __init__(self, tcp_handler):
        self.tcp_handler = tcp_handler

    def get_request_line(self):
        """
            Get a line, possibly preceded by a blank.
        """
        line = self.tcp_handler.rfile.readline()
        if line == "\r\n" or line == "\n":
            # Possible leftover from previous message
            line = self.tcp_handler.rfile.readline()
        return line

    def read_headers(self):
        """
            Read a set of headers.
            Stop once a blank line is reached.

            Return a ODictCaseless object, or None if headers are invalid.
        """
        ret = []
        name = ''
        while True:
            line = self.tcp_handler.rfile.readline()
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
                    value = line[i + 1:].strip()
                    ret.append([name, value])
                else:
                    return None
        return odict.ODictCaseless(ret)


    def read_chunked(self, limit, is_request):
        """
            Read a chunked HTTP body.

            May raise HttpError.
        """
        # FIXME: Should check if chunked is the final encoding in the headers
        # http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-16#section-3.3
        # 3.3 2.
        total = 0
        code = 400 if is_request else 502
        while True:
            line = self.tcp_handler.rfile.readline(128)
            if line == "":
                raise HttpErrorConnClosed(code, "Connection closed prematurely")
            if line != '\r\n' and line != '\n':
                try:
                    length = int(line, 16)
                except ValueError:
                    raise HttpError(
                        code,
                        "Invalid chunked encoding length: %s" % line
                    )
                total += length
                if limit is not None and total > limit:
                    msg = "HTTP Body too large. Limit is %s," \
                          " chunked content longer than %s" % (limit, total)
                    raise HttpError(code, msg)
                chunk = self.tcp_handler.rfile.read(length)
                suffix = self.tcp_handler.rfile.readline(5)
                if suffix != '\r\n':
                    raise HttpError(code, "Malformed chunked body")
                yield line, chunk, '\r\n'
                if length == 0:
                    return


    @classmethod
    def has_chunked_encoding(self, headers):
        return "chunked" in [
            i.lower() for i in http.get_header_tokens(headers, "transfer-encoding")
        ]


    @classmethod
    def parse_http_protocol(self, line):
        """
            Parse an HTTP protocol declaration.
            Returns a (major, minor) tuple, or None.
        """
        if not line.startswith("HTTP/"):
            return None
        _, version = line.split('/', 1)
        if "." not in version:
            return None
        major, minor = version.split('.', 1)
        try:
            major = int(major)
            minor = int(minor)
        except ValueError:
            return None
        return major, minor


    @classmethod
    def parse_init(self, line):
        try:
            method, url, protocol = string.split(line)
        except ValueError:
            return None
        httpversion = self.parse_http_protocol(protocol)
        if not httpversion:
            return None
        if not utils.isascii(method):
            return None
        return method, url, httpversion


    @classmethod
    def parse_init_connect(self, line):
        """
            Returns (host, port, httpversion) if line is a valid CONNECT line.
            http://tools.ietf.org/html/draft-luotonen-web-proxy-tunneling-01 section 3.1
        """
        v = self.parse_init(line)
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
        if not http.is_valid_port(port):
            return None
        if not http.is_valid_host(host):
            return None
        return host, port, httpversion

    @classmethod
    def parse_init_proxy(self, line):
        v = self.parse_init(line)
        if not v:
            return None
        method, url, httpversion = v

        parts = http.parse_url(url)
        if not parts:
            return None
        scheme, host, port, path = parts
        return method, scheme, host, port, path, httpversion

    @classmethod
    def parse_init_http(self, line):
        """
            Returns (method, url, httpversion)
        """
        v = self.parse_init(line)
        if not v:
            return None
        method, url, httpversion = v
        if not utils.isascii(url):
            return None
        if not (url.startswith("/") or url == "*"):
            return None
        return method, url, httpversion


    @classmethod
    def connection_close(self, httpversion, headers):
        """
            Checks the message to see if the client connection should be closed
            according to RFC 2616 Section 8.1 Note that a connection should be
            closed as well if the response has been read until end of the stream.
        """
        # At first, check if we have an explicit Connection header.
        if "connection" in headers:
            toks = http.get_header_tokens(headers, "connection")
            if "close" in toks:
                return True
            elif "keep-alive" in toks:
                return False

        # If we don't have a Connection header, HTTP 1.1 connections are assumed to
        # be persistent
        return httpversion != (1, 1)


    @classmethod
    def parse_response_line(self, line):
        parts = line.strip().split(" ", 2)
        if len(parts) == 2:  # handle missing message gracefully
            parts.append("")
        if len(parts) != 3:
            return None
        proto, code, msg = parts
        try:
            code = int(code)
        except ValueError:
            return None
        return (proto, code, msg)


    def read_http_body(self, *args, **kwargs):
        return "".join(
            content for _, content, _ in self.read_http_body_chunked(*args, **kwargs)
        )


    def read_http_body_chunked(
        self,
        headers,
        limit,
        request_method,
        response_code,
        is_request,
        max_chunk_size=None
    ):
        """
            Read an HTTP message body:
                headers: An ODictCaseless object
                limit: Size limit.
                is_request: True if the body to read belongs to a request, False
                otherwise
        """
        if max_chunk_size is None:
            max_chunk_size = limit or sys.maxsize

        expected_size = self.expected_http_body_size(
            headers, is_request, request_method, response_code
        )

        if expected_size is None:
            if self.has_chunked_encoding(headers):
                # Python 3: yield from
                for x in self.read_chunked(limit, is_request):
                    yield x
            else:  # pragma: nocover
                raise HttpError(
                    400 if is_request else 502,
                    "Content-Length unknown but no chunked encoding"
                )
        elif expected_size >= 0:
            if limit is not None and expected_size > limit:
                raise HttpError(
                    400 if is_request else 509,
                    "HTTP Body too large. Limit is %s, content-length was %s" % (
                        limit, expected_size
                    )
                )
            bytes_left = expected_size
            while bytes_left:
                chunk_size = min(bytes_left, max_chunk_size)
                yield "", self.tcp_handler.rfile.read(chunk_size), ""
                bytes_left -= chunk_size
        else:
            bytes_left = limit or -1
            while bytes_left:
                chunk_size = min(bytes_left, max_chunk_size)
                content = self.tcp_handler.rfile.read(chunk_size)
                if not content:
                    return
                yield "", content, ""
                bytes_left -= chunk_size
            not_done = self.tcp_handler.rfile.read(1)
            if not_done:
                raise HttpError(
                    400 if is_request else 509,
                    "HTTP Body too large. Limit is %s," % limit
                )


    @classmethod
    def expected_http_body_size(self, headers, is_request, request_method, response_code):
        """
            Returns the expected body length:
             - a positive integer, if the size is known in advance
             - None, if the size in unknown in advance (chunked encoding or invalid
             data)
             - -1, if all data should be read until end of stream.

            May raise HttpError.
        """
        # Determine response size according to
        # http://tools.ietf.org/html/rfc7230#section-3.3
        if request_method:
            request_method = request_method.upper()

        if (not is_request and (
                request_method == "HEAD" or
                (request_method == "CONNECT" and response_code == 200) or
                response_code in [204, 304] or
                100 <= response_code <= 199)):
            return 0
        if self.has_chunked_encoding(headers):
            return None
        if "content-length" in headers:
            try:
                size = int(headers["content-length"][0])
                if size < 0:
                    raise ValueError()
                return size
            except ValueError:
                return None
        if is_request:
            return 0
        return -1


    def read_request(self, include_body=True, body_size_limit=None):
        """
        Parse an HTTP request from a file stream

        Args:
            include_body (bool): Read response body as well
            body_size_limit (bool): Maximum body size
            wfile (file): If specified, HTTP Expect headers are handled
            automatically, by writing a HTTP 100 CONTINUE response to the stream.

        Returns:
            Request: The HTTP request

        Raises:
            HttpError: If the input is invalid.
        """
        httpversion, host, port, scheme, method, path, headers, content = (
            None, None, None, None, None, None, None, None)

        request_line = self.get_request_line()
        if not request_line:
            raise tcp.NetLibDisconnect()

        request_line_parts = self.parse_init(request_line)
        if not request_line_parts:
            raise HttpError(
                400,
                "Bad HTTP request line: %s" % repr(request_line)
            )
        method, path, httpversion = request_line_parts

        if path == '*' or path.startswith("/"):
            form_in = "relative"
            if not utils.isascii(path):
                raise HttpError(
                    400,
                    "Bad HTTP request line: %s" % repr(request_line)
                )
        elif method.upper() == 'CONNECT':
            form_in = "authority"
            r = self.parse_init_connect(request_line)
            if not r:
                raise HttpError(
                    400,
                    "Bad HTTP request line: %s" % repr(request_line)
                )
            host, port, _ = r
            path = None
        else:
            form_in = "absolute"
            r = self.parse_init_proxy(request_line)
            if not r:
                raise HttpError(
                    400,
                    "Bad HTTP request line: %s" % repr(request_line)
                )
            _, scheme, host, port, path, _ = r

        headers = self.read_headers()
        if headers is None:
            raise HttpError(400, "Invalid headers")

        expect_header = headers.get_first("expect", "").lower()
        if expect_header == "100-continue" and httpversion >= (1, 1):
            self.tcp_handler.wfile.write(
                'HTTP/1.1 100 Continue\r\n'
                '\r\n'
            )
            self.tcp_handler.wfile.flush()
            del headers['expect']

        if include_body:
            content = self.read_http_body(
                headers,
                body_size_limit,
                method,
                None,
                True
            )

        return self.Request(
            form_in,
            method,
            scheme,
            host,
            port,
            path,
            httpversion,
            headers,
            content
        )


    def read_response(self, request_method, body_size_limit, include_body=True):
        """
            Returns an http.Response

            By default, both response header and body are read.
            If include_body=False is specified, content may be one of the
            following:
            - None, if the response is technically allowed to have a response body
            - "", if the response must not have a response body (e.g. it's a
            response to a HEAD request)
        """

        line = self.tcp_handler.rfile.readline()
        # Possible leftover from previous message
        if line == "\r\n" or line == "\n":
            line = self.tcp_handler.rfile.readline()
        if not line:
            raise HttpErrorConnClosed(502, "Server disconnect.")
        parts = self.parse_response_line(line)
        if not parts:
            raise HttpError(502, "Invalid server response: %s" % repr(line))
        proto, code, msg = parts
        httpversion = self.parse_http_protocol(proto)
        if httpversion is None:
            raise HttpError(502, "Invalid HTTP version in line: %s" % repr(proto))
        headers = self.read_headers()
        if headers is None:
            raise HttpError(502, "Invalid headers.")

        if include_body:
            content = self.read_http_body(
                headers,
                body_size_limit,
                request_method,
                code,
                False
            )
        else:
            # if include_body==False then a None content means the body should be
            # read separately
            content = None
        return http.Response(httpversion, code, msg, headers, content)


    @classmethod
    def request_preamble(self, method, resource, http_major="1", http_minor="1"):
        return '%s %s HTTP/%s.%s' % (
            method, resource, http_major, http_minor
        )


    @classmethod
    def response_preamble(self, code, message=None, http_major="1", http_minor="1"):
        if message is None:
            message = status_codes.RESPONSES.get(code)
        return 'HTTP/%s.%s %s %s' % (http_major, http_minor, code, message)
