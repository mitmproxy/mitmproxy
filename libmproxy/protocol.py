import libmproxy.utils, libmproxy.flow
from netlib import http, http_status, tcp
import netlib.utils
from netlib.odict import ODictCaseless
import select
from proxy import ProxyError, KILL

LEGACY = True

def _handle(msg, conntype, connection_handler, *args, **kwargs):
    handler = None
    if conntype == "http":
        handler = HTTPHandler(connection_handler)
    else:
        raise NotImplementedError

    f = getattr(handler, "handle_" + msg)
    return f(*args, **kwargs)


def handle_messages(conntype, connection_handler):
    _handle("messages", conntype, connection_handler)


class ConnectionTypeChange(Exception):
    pass


class ProtocolHandler(object):
    def __init__(self, c):
        self.c = c


"""
Minimalistic cleanroom reimplemementation of a couple of flow.* classes. Most functionality is missing,
but they demonstrate what needs to be added/changed to/within the existing classes.
"""


class Flow(object):
    def __init__(self, conntype, client_conn, server_conn, error):
        self.conntype = conntype
        self.client_conn, self.server_conn = client_conn, server_conn
        self.error = error


class HTTPFlow(Flow):
    def __init__(self, client_conn, server_conn, error, request, response):
        Flow.__init__(self, "http", client_conn, server_conn, error)
        self.request, self.response = request, response


class HttpAuthenticationError(Exception):
    def __init__(self, auth_headers=None):
        self.auth_headers = auth_headers

    def __str__(self):
        return "HttpAuthenticationError"


class HTTPMessage(object):
    def _assemble_headers(self):
        headers = self.headers.copy()
        libmproxy.utils.del_all(headers,
                                ["proxy-connection",
                                 "transfer-encoding"])
        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        elif 'Transfer-Encoding' in self.headers:  # content-length for e.g. chuncked transfer-encoding with no content
            headers["Content-Length"] = ["0"]

        return str(headers)


class HTTPResponse(HTTPMessage):
    def __init__(self, httpversion, code, msg, headers, content, timestamp_start, timestamp_end):
        self.httpversion = httpversion
        self.code = code
        self.msg = msg
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

        assert isinstance(headers, ODictCaseless)

    #FIXME: Compatibility Fix
    @property
    def request(self):
        return False

    def _assemble_response_line(self):
        return 'HTTP/%s.%s %s %s' % (self.httpversion[0], self.httpversion[1], self.code, self.msg)

    def _assemble(self):
        response_line = self._assemble_response_line()
        return '%s\r\n%s\r\n%s' % (response_line, self._assemble_headers(), self.content)

    @classmethod
    def from_stream(cls, rfile, request_method, include_content=True, body_size_limit=None):
        """
        Parse an HTTP response from a file stream
        """
        if not include_content:
            raise NotImplementedError

        httpversion, code, msg, headers, content = http.read_response(
            rfile,
            request_method,
            body_size_limit)
        timestamp_start = rfile.first_byte_timestamp
        timestamp_end = libmproxy.utils.timestamp()
        return HTTPResponse(httpversion, code, msg, headers, content, timestamp_start, timestamp_end)


class HTTPRequest(HTTPMessage):
    def __init__(self, form_in, method, scheme, host, port, path, httpversion, headers, content,
                 timestamp_start, timestamp_end, form_out=None, ip=None):
        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.httpversion = httpversion
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

        self.form_out = form_out or self.form_in
        self.ip = ip  # resolved ip address
        assert isinstance(headers, ODictCaseless)

    #FIXME: Compatibility Fix
    def is_live(self):
        return True

    def _assemble_request_line(self, form=None):
        form = form or self.form_out
        request_line = None
        if form == "asterisk" or form == "origin":
            request_line = '%s %s HTTP/%s.%s' % (self.method, self.path, self.httpversion[0], self.httpversion[1])
        elif form == "authority":
            request_line = '%s %s:%s HTTP/%s.%s' % (self.method, self.host, self.port,
                                                    self.httpversion[0], self.httpversion[1])
        elif form == "absolute":
            request_line = '%s %s://%s:%s%s HTTP/%s.%s' % \
                           (self.method, self.scheme, self.host, self.port, self.path,
                            self.httpversion[0], self.httpversion[1])
        else:
            raise http.HttpError(400, "Invalid request form")
        return request_line

    def _assemble(self):
        request_line = self._assemble_request_line()
        return '%s\r\n%s\r\n%s' % (request_line, self._assemble_headers(), self.content)

    @classmethod
    def from_stream(cls, rfile, include_content=True, body_size_limit=None):
        """
        Parse an HTTP request from a file stream
        """
        httpversion, host, port, scheme, method, path, headers, content, timestamp_start, timestamp_end \
            = None, None, None, None, None, None, None, None, None, None

        request_line = HTTPHandler.get_line(rfile)
        timestamp_start = rfile.first_byte_timestamp

        request_line_parts = http.parse_init(request_line)
        if not request_line_parts:
            raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        method, path, httpversion = request_line_parts

        if path == '*':
            form_in = "asterisk"
        elif path.startswith("/"):
            form_in = "origin"
            if not netlib.utils.isascii(path):
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        elif method.upper() == 'CONNECT':
            form_in = "authority"
            r = http.parse_init_connect(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            host, port, _ = r
        else:
            form_in = "absolute"
            r = http.parse_init_proxy(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            _, scheme, host, port, path, _ = r

        headers = http.read_headers(rfile)
        if headers is None:
            raise http.HttpError(400, "Invalid headers")

        if include_content:
            content = http.read_http_body(rfile, headers, body_size_limit, True)
            timestamp_end = libmproxy.utils.timestamp()

        return HTTPRequest(form_in, method, scheme, host, port, path, httpversion, headers, content,
                           timestamp_start, timestamp_end)


class HTTPHandler(ProtocolHandler):
    def handle_messages(self):
        while self.handle_flow():
            pass
        self.c.close = True

    def get_response_from_server(self, request):
        request_raw = request._assemble()

        for i in range(2):
            try:
                self.c.server_conn.wfile.write(request_raw)
                self.c.server_conn.wfile.flush()
                return HTTPResponse.from_stream(self.c.server_conn.rfile, request.method,
                                                body_size_limit=self.c.config.body_size_limit)
            except (tcp.NetLibDisconnect, http.HttpErrorConnClosed), v:
                self.c.log("error in server communication: %s" % str(v))
                if i < 1:
                    # In any case, we try to reconnect at least once.
                    # This is necessary because it might be possible that we already initiated an upstream connection
                    # after clientconnect that has already been expired, e.g consider the following event log:
                    # > clientconnect (transparent mode destination known)
                    # > serverconnect
                    # > read n% of large request
                    # > server detects timeout, disconnects
                    # > read (100-n)% of large request
                    # > send large request upstream
                    self.c.server_reconnect()
                else:
                    raise v

    def handle_flow(self):
        flow = HTTPFlow(self.c.client_conn, self.c.server_conn, None, None, None)
        try:
            flow.request = HTTPRequest.from_stream(self.c.client_conn.rfile,
                                                   body_size_limit=self.c.config.body_size_limit)
            self.c.log("request", [flow.request._assemble_request_line(flow.request.form_in)])
            self.process_request(flow.request)

            request_reply = self.c.channel.ask("request" if LEGACY else "httprequest",
                                               flow.request if LEGACY else flow)
            if request_reply is None or request_reply == KILL:
                return False

            if isinstance(request_reply, HTTPResponse):
                flow.response = request_reply
            else:
                flow.response = self.get_response_from_server(flow.request)

            self.c.log("response", [flow.response._assemble_response_line()])
            response_reply = self.c.channel.ask("response" if LEGACY else "httpresponse",
                                                flow.response if LEGACY else flow)
            if response_reply is None or response_reply == KILL:
                return False

            raw = flow.response._assemble()
            self.c.client_conn.wfile.write(raw)
            self.c.client_conn.wfile.flush()
            flow.timestamp_end = libmproxy.utils.timestamp()

            if (http.connection_close(flow.request.httpversion, flow.request.headers) or
                    http.connection_close(flow.response.httpversion, flow.response.headers)):
                return False

            if flow.request.form_in == "authority":
                self.ssl_upgrade(flow.request)
            return True
        except HttpAuthenticationError, e:
            self.process_error(flow, code=407, message="Proxy Authentication Required", headers=e.auth_headers)
        except (http.HttpError, ProxyError), e:
            self.process_error(flow, code=e.code, message=e.msg)
        except tcp.NetLibError, e:
            self.process_error(flow, message=e.message or e.__class__)
        return False

    def process_error(self, flow, code=None, message=None, headers=None):
        try:
            err = ("%s: %s" % (code, message)) if code else message
            flow.error = libmproxy.flow.Error(False, err)
            self.c.log("error: %s" % err)
            self.c.channel.ask("error" if LEGACY else "httperror",
                               flow.error if LEGACY else flow)
            if code:
                self.send_error(code, message, headers)
        except:
            pass

    def send_error(self, code, message, headers):
        response = http_status.RESPONSES.get(code, "Unknown")
        html_content = '<html><head>\n<title>%d %s</title>\n</head>\n<body>\n%s\n</body>\n</html>' % \
                       (code, response, message)
        self.c.client_conn.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
        self.c.client_conn.wfile.write("Server: %s\r\n" % self.c.server_version)
        self.c.client_conn.wfile.write("Content-type: text/html\r\n")
        self.c.client_conn.wfile.write("Content-Length: %d\r\n" % len(html_content))
        if headers:
            for key, value in headers.items():
                self.c.client_conn.wfile.write("%s: %s\r\n" % (key, value))
        self.c.client_conn.wfile.write("Connection: close\r\n")
        self.c.client_conn.wfile.write("\r\n")
        self.c.client_conn.wfile.write(html_content)
        self.c.client_conn.wfile.flush()

    def ssl_upgrade(self, upstream_request=None):
        """
        Upgrade the connection to SSL after an authority (CONNECT) request has been made.
        If the authority request has been forwarded upstream (because we have another proxy server there),
        money-patch the ConnectionHandler.server_reconnect function to resend the request on reconnect.

        This isn't particular beautiful code, but it isolates this rare edge-case from the
        protocol-agnostic ConnectionHandler
        """
        self.c.mode = "transparent"
        self.c.determine_conntype()
        self.c.establish_ssl(server=True, client=True)

        if upstream_request:
            self.c.log("Hook reconnect function")
            original_reconnect_func = self.c.server_reconnect

            def reconnect_http_proxy():
                self.c.log("Hooked reconnect function")
                self.c.log("Hook: Run original redirect")
                original_reconnect_func(no_ssl=True)
                self.c.log("Hook: Write CONNECT request to upstream proxy", [upstream_request._assemble_request_line()])
                self.c.server_conn.wfile.write(upstream_request._assemble())
                self.c.server_conn.wfile.flush()
                self.c.log("Hook: Read answer to CONNECT request from proxy")
                resp = HTTPResponse.from_stream(self.c.server_conn.rfile, upstream_request.method)
                if resp.code != 200:
                    raise ProxyError(resp.code, 
                                     "Cannot reestablish SSL connection with upstream proxy: \r\n" + str(resp.headers))
                self.c.log("Hook: Establish SSL with upstream proxy")
                self.c.establish_ssl(server=True)

            self.c.server_reconnect = reconnect_http_proxy

        raise ConnectionTypeChange

    def process_request(self, request):
        if self.c.mode == "regular":
            self.authenticate(request)
        if request.form_in == "authority" and self.c.client_conn.ssl_established:
            raise http.HttpError(502, "Must not CONNECT on already encrypted connection")

        # If we have a CONNECT request, we might need to intercept
        if request.form_in == "authority":
            directly_addressed_at_mitmproxy = (self.c.mode == "regular") and not self.c.config.forward_proxy
            if directly_addressed_at_mitmproxy:
                self.c.establish_server_connection(request.host, request.port)
                self.c.client_conn.wfile.write(
                    'HTTP/1.1 200 Connection established\r\n' +
                    ('Proxy-agent: %s\r\n' % self.c.server_version) +
                    '\r\n'
                )
                self.c.client_conn.wfile.flush()
                self.ssl_upgrade()  # raises ConnectionTypeChange exception

        if self.c.mode == "regular":
            if request.form_in == "authority":
                pass
            elif request.form_in == "absolute":
                if not self.c.config.forward_proxy:
                    request.form_out = "origin"
                    if ((not self.c.server_conn) or
                            (self.c.server_conn.address != (request.host, request.port))):
                        self.c.establish_server_connection(request.host, request.port)
            else:
                raise http.HttpError(400, "Invalid Request")

    def authenticate(self, request):
        if self.c.config.authenticator:
            if self.c.config.authenticator.authenticate(request.headers):
                self.c.config.authenticator.clean(request.headers)
            else:
                raise HttpAuthenticationError(self.c.config.authenticator.auth_challenge_headers())
        return request.headers

    @staticmethod
    def get_line(fp):
        """
            Get a line, possibly preceded by a blank.
        """
        line = fp.readline()
        if line == "\r\n" or line == "\n":  # Possible leftover from previous message
            line = fp.readline()
        if line == "":
            raise tcp.NetLibDisconnect
        return line