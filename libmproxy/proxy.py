"""
    A simple proxy server implementation, which always reads all of a server
    response into memory, performs some transformation, and then writes it back
    to the client. 

    Development started from Neil Schemenauer's munchy.py
"""
import sys, os, time, string, socket, urlparse, re, select, copy
import SocketServer, ssl
import utils, controller

NAME = "mitmproxy"
config = None


class ProxyError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class Config:
    def __init__(self, pemfile):
        self.pemfile = pemfile


def try_del(dict, key):
    try:
        del dict[key]
    except KeyError:
        pass


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.
    """
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    if not scheme:
        return None
    if ':' in netloc:
        host, port = string.split(netloc, ':')
        port = int(port)
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path:
        path = "/"
    return scheme, host, port, path


def parse_proxy_request(request):
    """
        Parse a proxy request line. Return (method, scheme, host, port, path).
        Raise ProxyError on error.
    """
    try:
        method, url, protocol = string.split(request)
    except ValueError:
        raise ProxyError(400, "Can't parse request")
    if method in ['GET', 'HEAD', 'POST']:
        if url.startswith("/"):
            scheme, port, host, path = None, None, None, url
        else:
            parts = parse_url(url)
            if not parts:
                raise ProxyError(400, "Invalid url: %s"%url)
            scheme, host, port, path = parts
    elif method == 'CONNECT':
        scheme = None
        path = None
        host, port = url.split(":")
        port = int(port)
    else:
        raise ProxyError(501, "Unknown request method: %s" % method)
    return method, scheme, host, port, path


class Request(controller.Msg):
    FMT = '%s %s HTTP/1.0\r\n%s\r\n%s'
    def __init__(self, client_conn, host, port, scheme, method, path, headers, content, timestamp=None):
        self.client_conn = client_conn
        self.host, self.port, self.scheme = host, port, scheme
        self.method, self.path, self.headers, self.content = method, path, headers, content
        self.timestamp = timestamp or time.time()
        controller.Msg.__init__(self)

    def get_state(self):
        return dict(
            host = self.host,
            port = self.port,
            scheme = self.scheme,
            method = self.method,
            path = self.path,
            headers = self.headers.get_state(),
            content = self.content,
            timestamp = self.timestamp,
        )

    @classmethod
    def from_state(klass, client_conn, state):
        return klass(
            client_conn,
            state["host"],
            state["port"],
            state["scheme"],
            state["method"],
            state["path"],
            utils.Headers.from_state(state["headers"]),
            state["content"],
            state["timestamp"]
        )

    def __eq__(self, other):
        return self.get_state() == other.get_state()

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def url(self):
        if (self.port, self.scheme) in [(80, "http"), (443, "https")]:
            host = self.host
        else:
            host = "%s:%s"%(self.host, self.port)
        return "%s://%s%s"%(self.scheme, host, self.path)

    def set_url(self, url):
        parts = parse_url(url)
        if not parts:
            return False
        self.scheme, self.host, self.port, self.path = parts
        return True

    def is_response(self):
        return False

    def short(self):
        return "%s %s"%(self.method, self.url())

    def assemble(self):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.
        """
        headers = self.headers.copy()
        try_del(headers, 'accept-encoding')
        try_del(headers, 'proxy-connection')
        try_del(headers, 'keep-alive')
        try_del(headers, 'connection')
        headers["connection"] = ["close"]
        data = (self.method, self.path, str(headers), self.content)
        return self.FMT%data


class Response(controller.Msg):
    FMT = '%s\r\n%s\r\n%s'
    def __init__(self, request, code, proto, msg, headers, content, timestamp=None):
        self.request = request
        self.code, self.proto, self.msg = code, proto, msg
        self.headers, self.content = headers, content
        self.timestamp = timestamp or time.time()
        controller.Msg.__init__(self)

    def get_state(self):
        return dict(
            code = self.code,
            proto = self.proto,
            msg = self.msg,
            headers = self.headers.get_state(),
            timestamp = self.timestamp,
            content = self.content
        )

    @classmethod
    def from_state(klass, request, state):
        return klass(
            request,
            state["code"],
            state["proto"],
            state["msg"],
            utils.Headers.from_state(state["headers"]),
            state["content"],
            state["timestamp"],
        )

    def __eq__(self, other):
        return self.get_state() == other.get_state()

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def is_response(self):
        return True

    def short(self):
        return "%s %s"%(self.code, self.proto)

    def assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.
        """
        headers = self.headers.copy()
        try_del(headers, 'accept-encoding')
        try_del(headers, 'proxy-connection')
        try_del(headers, 'connection')
        try_del(headers, 'keep-alive')
        headers["connection"] = ["close"]
        proto = "%s %s %s"%(self.proto, self.code, self.msg)
        data = (proto, str(headers), self.content)
        return self.FMT%data


class ClientConnection(controller.Msg):
    def __init__(self, address):
        """
            address is an (address, port) tuple, or None if this connection has
            been replayed from within mitmproxy.
        """
        self.address = address
        controller.Msg.__init__(self)

    def get_state(self):
        return self.address

    @classmethod
    def from_state(klass, state):
        return klass(state)

    def set_replay(self):
        self.address = None

    def is_replay(self):
        if self.address:
            return False
        else:
            return True

    def copy(self):
        return copy.copy(self)


class Error(controller.Msg):
    def __init__(self, client_conn, msg, timestamp=None):
        self.client_conn, self.msg = client_conn, msg
        self.timestamp = timestamp or time.time()
        controller.Msg.__init__(self)

    def copy(self):
        return copy.copy(self)

    def get_state(self):
        return dict(
            msg = self.msg,
            timestamp = self.timestamp,
        )

    @classmethod
    def from_state(klass, state):
        return klass(
            None,
            state["msg"],
            state["timestamp"],
        )

    def __eq__(self, other):
        return self.get_state() == other.get_state()


class FileLike:
    def __init__(self, o):
        self.o = o

    def __getattr__(self, attr):
        return getattr(self.o, attr)

    def flush(self):
        pass

    def read(self, length):
        result = ''
        while len(result) < length:
            data = self.o.read(length)
            if not data:
                break
            result += data
        return result

    def readline(self):
        result = ''
        while True:
            ch = self.read(1)
            if not ch:
                break
            else:
                result += ch
                if ch == '\n':
                    break
        return result


#begin nocover

class ServerConnection:
    def __init__(self, request):
        self.request = request
        self.server, self.rfile, self.wfile = None, None, None
        self.connect()
        self.send_request()

    def connect(self):
        try:
            addr = socket.gethostbyname(self.request.host)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.request.scheme == "https":
                server = ssl.wrap_socket(server)
            server.connect((addr, self.request.port))
        except socket.error, err:
            raise ProxyError(200, 'Error connecting to "%s": %s' % (self.request.host, err))
        self.server = server
        self.rfile, self.wfile = server.makefile('rb'), server.makefile('wb')

    def send_request(self):
        try:
            self.wfile.write(self.request.assemble())
            self.wfile.flush()
        except socket.error, err:
            raise ProxyError(500, 'Error sending data to "%s": %s' % (request.host, err))

    def read_response(self):
        proto = self.rfile.readline()
        if not proto:
            raise ProxyError(200, "Blank server response.")
        parts = proto.strip().split(" ", 2)
        if not len(parts) == 3:
            raise ProxyError(200, "Invalid server response: %s."%proto)
        proto, code, msg = parts
        code = int(code)
        headers = utils.Headers()
        headers.read(self.rfile)
        if headers.has_key("content-length"):
            content = self.rfile.read(int(headers["content-length"][0]))
        else:
            content = self.rfile.read()
        return Response(self.request, code, proto, msg, headers, content)

    def terminate(self):
        try:
            if not self.wfile.closed:
                self.wfile.flush()
            self.server.close()
        except IOError:
            pass


class ProxyHandler(SocketServer.StreamRequestHandler):
    def __init__(self, request, client_address, server, q):
        self.mqueue = q
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        server = None
        cc = ClientConnection(self.client_address)
        cc.send(self.mqueue)
        try:
            request = self.read_request(cc)
            request = request.send(self.mqueue)
            if request is None:
                self.finish()
                return
            if request.is_response():
                response = request
                request = False
                response = response.send(self.mqueue)
            else:
                server = ServerConnection(request)
                response = server.read_response()
                response = response.send(self.mqueue)
                if response is None:
                    server.terminate()
            if response is None:
                self.finish()
                return
            self.send_response(response)
        except IOError:
            pass
        except ProxyError, e:
            err = Error(cc, e.msg)
            err.send(self.mqueue)
            self.send_error(e.code, e.msg)
        if server:
            server.terminate()
        self.finish()

    def read_request(self, client_conn):
        request = self.rfile.readline()
        method, scheme, host, port, path = parse_proxy_request(request)
        if not host:
            raise ProxyError(200, 'Invalid request: %s'%request)
        if method == "CONNECT":
            # Discard additional headers sent to the proxy. Should I expose
            # these to users?
            while 1:
                d = self.rfile.readline()
                if not d.strip():
                    break
            self.wfile.write('HTTP/1.1 200 Connection established\r\n')
            self.wfile.write('Proxy-agent: %s\r\n'%NAME)
            self.wfile.write('\r\n')
            self.wfile.flush()
            self.connection = ssl.wrap_socket(
                self.connection,
                certfile = config.pemfile,
                keyfile = config.pemfile,
                server_side = True,
                ssl_version = ssl.PROTOCOL_SSLv23,
                do_handshake_on_connect = False
            )
            self.rfile = FileLike(self.connection)
            self.wfile = FileLike(self.connection)
            method, _, _, _, path = parse_proxy_request(self.rfile.readline())
            scheme = "https"
        headers = utils.Headers()
        headers.read(self.rfile)
        if method == 'POST' and not headers.has_key('content-length'):
            raise ProxyError(400, "Missing Content-Length for POST method")
        if headers.has_key("content-length") and int(headers["content-length"][0]):
            content = self.rfile.read(int(headers["content-length"][0]))
        else:
            content = ""
        return Request(client_conn, host, port, scheme, method, path, headers, content)

    def send_response(self, response):
        self.wfile.write(response.assemble())
        self.wfile.flush()

    def terminate(self, connection, wfile, rfile):
        self.request.close()
        try:
            if not getattr(wfile, "closed", False):
                wfile.flush()
            connection.close()
        except IOError:
            pass

    def finish(self):
        self.terminate(self.connection, self.wfile, self.rfile)

    def send_error(self, code, body):
        try:
            import BaseHTTPServer
            response = BaseHTTPServer.BaseHTTPRequestHandler.responses[code][0]
            self.wfile.write("HTTP/1.0 %s %s\r\n" % (code, response))
            self.wfile.write("Server: %s\r\n"%NAME)
            self.wfile.write("Content-type: text/html\r\n")
            self.wfile.write("\r\n")
            self.wfile.write('<html><head>\n<title>%d %s</title>\n</head>\n'
                    '<body>\n%s\n</body>\n</html>' % (code, response, body))
            self.wfile.flush()
            self.wfile.close()
            self.rfile.close()
        except IOError:
            pass


ServerBase = SocketServer.ThreadingTCPServer
ServerBase.daemon_threads = True        # Terminate workers when main thread terminates
class ProxyServer(ServerBase):
    request_queue_size = 20
    allow_reuse_address = True
    def __init__(self, port, address=''):
        self.port, self.address = port, address
        ServerBase.__init__(self, (address, port), ProxyHandler)
        self.masterq = None

    def set_mqueue(self, q):
        self.masterq = q

    def process_request(self, request, client_address):
        return ServerBase.process_request(self, request, client_address)

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, self.masterq)

