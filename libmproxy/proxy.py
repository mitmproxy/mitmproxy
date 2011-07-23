"""
    A simple proxy server implementation, which always reads all of a server
    response into memory, performs some transformation, and then writes it back
    to the client.

    Development started from Neil Schemenauer's munchy.py
"""
import sys, os, string, socket, urlparse, re, select, copy, base64, time, Cookie
from email.utils import parsedate_tz, formatdate, mktime_tz
import shutil, tempfile
import optparse, SocketServer, ssl
import utils, controller, encoding

NAME = "mitmproxy"


class ProxyError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class SSLConfig:
    def __init__(self, certfile = None, ciphers = None, cacert = None, cert_wait_time=None):
        self.certfile = certfile
        self.ciphers = ciphers
        self.cacert = cacert
        self.certdir = None
        self.cert_wait_time = cert_wait_time


def read_chunked(fp):
    content = ""
    while 1:
        line = fp.readline()
        if line == "":
            raise IOError("Connection closed")
        if line == '\r\n' or line == '\n':
            continue
        length = int(line,16)
        if not length:
            break
        content += fp.read(length)
        line = fp.readline()
        if line != '\r\n':
            raise IOError("Malformed chunked body")
    while 1:
        line = fp.readline()
        if line == "":
            raise IOError("Connection closed")
        if line == '\r\n' or line == '\n':
            break
    return content


def read_http_body(rfile, connection, headers, all):
    if 'transfer-encoding' in headers:
        if not ",".join(headers["transfer-encoding"]) == "chunked":
            raise IOError('Invalid transfer-encoding')
        content = read_chunked(rfile)
    elif "content-length" in headers:
        content = rfile.read(int(headers["content-length"][0]))
    elif all:
        content = rfile.read()
        connection.close = True
    else:
        content = ""
    return content


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
    if not path.startswith("/"):
        path = "/" + path
    return scheme, host, port, path


def parse_request_line(request):
    """
        Parse a proxy request line. Return (method, scheme, host, port, path, minor).
        Raise ProxyError on error.
    """
    try:
        method, url, protocol = string.split(request)
    except ValueError:
        raise ProxyError(400, "Can't parse request")
    if method == 'CONNECT':
        scheme = None
        path = None
        try:
            host, port = url.split(":")
        except ValueError:
            raise ProxyError(400, "Can't parse request")
        port = int(port)
    else:
        if url.startswith("/") or url == "*":
            scheme, port, host, path = None, None, None, url
        else:
            parts = parse_url(url)
            if not parts:
                raise ProxyError(400, "Invalid url: %s"%url)
            scheme, host, port, path = parts
    if not protocol.startswith("HTTP/"):
        raise ProxyError(400, "Unsupported protocol")
    major,minor = protocol.split('/')[1].split('.')
    major = int(major)
    minor = int(minor)
    if major != 1:
        raise ProxyError(400, "Unsupported protocol")
    return method, scheme, host, port, path, minor


class Request(controller.Msg):
    FMT = '%s %s HTTP/1.1\r\n%s\r\n%s'
    FMT_PROXY = '%s %s://%s:%s%s HTTP/1.1\r\n%s\r\n%s'
    def __init__(self, client_conn, host, port, scheme, method, path, headers, content, timestamp=None):
        self.client_conn = client_conn
        self.host, self.port, self.scheme = host, port, scheme
        self.method, self.path, self.headers, self.content = method, path, headers, content
        self.timestamp = timestamp or utils.timestamp()
        self.close = False
        controller.Msg.__init__(self)

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False

    def anticache(self):
        """
            Modifies this request to remove headers that might produce a cached
            response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            "if-modified-since",
            "if-none-match",
        ]
        for i in delheaders:
            del self.headers[i]

    def anticomp(self):
        """
            Modifies this request to remove headers that will compress the
            resource's data.
        """
        self.headers["accept-encoding"] = ["identity"]

    def constrain_encoding(self):
        """
            Limits the permissible Accept-Encoding values, based on what we can
            decode appropriately.
        """
        if self.headers["accept-encoding"]:
            self.headers["accept-encoding"] = [', '.join([
                e for e in encoding.ENCODINGS if e in self.headers["accept-encoding"][0]
            ])]

    def set_replay(self):
        self.client_conn = None

    def is_replay(self):
        if self.client_conn:
            return False
        else:
            return True

    def load_state(self, state):
        if state["client_conn"]:
            if self.client_conn:
                self.client_conn.load_state(state["client_conn"])
            else:
                self.client_conn = ClientConnect.from_state(state["client_conn"])
        else:
            self.client_conn = None
        self.host = state["host"]
        self.port = state["port"]
        self.scheme = state["scheme"]
        self.method = state["method"]
        self.path = state["path"]
        self.headers = utils.Headers.from_state(state["headers"])
        self.content = base64.decodestring(state["content"])
        self.timestamp = state["timestamp"]

    def get_state(self):
        return dict(
            client_conn = self.client_conn.get_state() if self.client_conn else None,
            host = self.host,
            port = self.port,
            scheme = self.scheme,
            method = self.method,
            path = self.path,
            headers = self.headers.get_state(),
            content = base64.encodestring(self.content),
            timestamp = self.timestamp,
        )

    @classmethod
    def from_state(klass, state):
        return klass(
            ClientConnect.from_state(state["client_conn"]),
            str(state["host"]),
            state["port"],
            str(state["scheme"]),
            str(state["method"]),
            str(state["path"]),
            utils.Headers.from_state(state["headers"]),
            base64.decodestring(state["content"]),
            state["timestamp"]
        )

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self.get_state() == other.get_state()

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def hostport(self):
        if (self.port, self.scheme) in [(80, "http"), (443, "https")]:
            host = self.host
        else:
            host = "%s:%s"%(self.host, self.port)
        return host

    def url(self):
        return "%s://%s%s"%(self.scheme, self.hostport(), self.path)

    def set_url(self, url):
        parts = parse_url(url)
        if not parts:
            return False
        self.scheme, self.host, self.port, self.path = parts
        return True

    def is_response(self):
        return False

    def assemble(self, _proxy = False):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.
        """
        headers = self.headers.copy()
        utils.try_del(headers, 'proxy-connection')
        utils.try_del(headers, 'keep-alive')
        utils.try_del(headers, 'connection')
        utils.try_del(headers, 'content-length')
        utils.try_del(headers, 'transfer-encoding')
        if not 'host' in headers:
            headers["host"] = [self.hostport()]
        content = self.content
        if content is not None:
            headers["content-length"] = [str(len(content))]
        else:
            content = ""
        if self.close:
            headers["connection"] = ["close"]
        if not _proxy:
            return self.FMT % (self.method, self.path, str(headers), content)
        else:
            return self.FMT_PROXY % (self.method, self.scheme, self.host, self.port, self.path, str(headers), content)

    def replace(self, pattern, repl, count=0, flags=0):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Returns the number of replacements
            made. 
        """
        self.content, c = re.subn(pattern, repl, self.content, count, flags)
        self.path, pc = re.subn(pattern, repl, self.path, count, flags)
        c += pc
        c += self.headers.replace(pattern, repl, count, flags)
        return c


class Response(controller.Msg):
    FMT = '%s\r\n%s\r\n%s'
    def __init__(self, request, code, msg, headers, content, timestamp=None):
        self.request = request
        self.code, self.msg = code, msg
        self.headers, self.content = headers, content
        self.timestamp = timestamp or utils.timestamp()
        controller.Msg.__init__(self)
        self.replay = False

    def _refresh_cookie(self, c, delta):
        """
            Takes a cookie string c and a time delta in seconds, and returns
            a refreshed cookie string.
        """
        c = Cookie.SimpleCookie(str(c))
        for i in c.values():
            if "expires" in i:
                d = parsedate_tz(i["expires"])
                if d:
                    d = mktime_tz(d) + delta
                    i["expires"] = formatdate(d)
                else:
                    # This can happen when the expires tag is invalid.
                    # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                    # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                    # strictly correct according tot he cookie spec. Browsers
                    # appear to parse this tolerantly - maybe we should too.
                    # For now, we just ignore this.
                    del i["expires"]
        return c.output(header="").strip()

    def refresh(self, now=None):
        """
            This fairly complex and heuristic function refreshes a server
            response for replay.

                - It adjusts date, expires and last-modified headers.
                - It adjusts cookie expiration.
        """
        if not now:
            now = time.time()
        delta = now - self.timestamp
        refresh_headers = [
            "date",
            "expires",
            "last-modified",
        ]
        for i in refresh_headers:
            if i in self.headers:
                d = parsedate_tz(self.headers[i][0])
                if d:
                    new = mktime_tz(d) + delta
                    self.headers[i] = [formatdate(new)]
        c = []
        for i in self.headers["set-cookie"]:
            c.append(self._refresh_cookie(i, delta))
        if c:
            self.headers["set-cookie"] = c

    def set_replay(self):
        self.replay = True

    def is_replay(self):
        return self.replay

    def load_state(self, state):
        self.code = state["code"]
        self.msg = state["msg"]
        self.headers = utils.Headers.from_state(state["headers"])
        self.content = base64.decodestring(state["content"])
        self.timestamp = state["timestamp"]

    def get_state(self):
        return dict(
            code = self.code,
            msg = self.msg,
            headers = self.headers.get_state(),
            timestamp = self.timestamp,
            content = base64.encodestring(self.content)
        )

    @classmethod
    def from_state(klass, request, state):
        return klass(
            request,
            state["code"],
            str(state["msg"]),
            utils.Headers.from_state(state["headers"]),
            base64.decodestring(state["content"]),
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

    def assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.
        """
        headers = self.headers.copy()
        utils.try_del(headers, 'proxy-connection')
        utils.try_del(headers, 'connection')
        utils.try_del(headers, 'keep-alive')
        utils.try_del(headers, 'transfer-encoding')
        content = self.content
        if content is not None:
            headers["content-length"] = [str(len(content))]
        else:
            content = ""
        if self.request.client_conn.close:
            headers["connection"] = ["close"]
        proto = "HTTP/1.1 %s %s"%(self.code, str(self.msg))
        data = (proto, str(headers), content)
        return self.FMT%data

    def replace(self, pattern, repl, count=0, flags=0):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the response. Returns the number of replacements
            made. 
        """
        self.content, c = re.subn(pattern, repl, self.content, count, flags)
        c += self.headers.replace(pattern, repl, count, flags)
        return c


class ClientDisconnect(controller.Msg):
    def __init__(self, client_conn):
        controller.Msg.__init__(self)
        self.client_conn = client_conn


class ClientConnect(controller.Msg):
    def __init__(self, address):
        """
            address is an (address, port) tuple, or None if this connection has
            been replayed from within mitmproxy.
        """
        self.address = address
        self.close = False
        self.requestcount = 0
        self.connection_error = None
        controller.Msg.__init__(self)

    def __eq__(self, other):
        return self.get_state() == other.get_state()

    def load_state(self, state):
        self.address = state

    def get_state(self):
        return list(self.address) if self.address else None

    @classmethod
    def from_state(klass, state):
        if state:
            return klass(state)
        else:
            return None

    def copy(self):
        return copy.copy(self)


class Error(controller.Msg):
    def __init__(self, request, msg, timestamp=None):
        self.request, self.msg = request, msg
        self.timestamp = timestamp or utils.timestamp()
        controller.Msg.__init__(self)

    def load_state(self, state):
        self.msg = state["msg"]
        self.timestamp = state["timestamp"]

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

    def replace(self, pattern, repl, count=0, flags=0):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Returns the number of replacements
            made. 
        """
        self.msg, c = re.subn(pattern, repl, self.msg, count, flags)
        return c


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
            try:
                data = self.o.read(length)
            except AttributeError:
                break
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
        self.host = request.host
        self.port = request.port
        self.scheme = request.scheme
        self.close = False
        self.server, self.rfile, self.wfile = None, None, None
        self.connect()

    def connect(self):
        try:
            addr = socket.gethostbyname(self.host)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.scheme == "https":
                server = ssl.wrap_socket(server)
            server.connect((addr, self.port))
        except socket.error, err:
            raise ProxyError(504, 'Error connecting to "%s": %s' % (self.host, err))
        self.server = server
        self.rfile, self.wfile = server.makefile('rb'), server.makefile('wb')

    def send_request(self, request):
        self.request = request
        request.close = self.close
        try:
            self.wfile.write(request.assemble())
            self.wfile.flush()
        except socket.error, err:
            raise ProxyError(504, 'Error sending data to "%s": %s' % (request.host, err))

    def read_response(self):
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if not line:
            raise ProxyError(502, "Blank server response.")
        parts = line.strip().split(" ", 2)
        if not len(parts) == 3:
            raise ProxyError(502, "Invalid server response: %s."%line)
        proto, code, msg = parts
        code = int(code)
        headers = utils.Headers()
        headers.read(self.rfile)
        if code >= 100 and code <= 199:
            return self.read_response()
        if self.request.method == "HEAD" or code == 204 or code == 304:
            content = ""
        else:
            content = read_http_body(self.rfile, self, headers, True)
        return Response(self.request, code, msg, headers, content)

    def terminate(self):
        try:
            if not self.wfile.closed:
                self.wfile.flush()
            self.server.close()
        except IOError:
            pass


class ProxyHandler(SocketServer.StreamRequestHandler):
    def __init__(self, config, request, client_address, server, q):
        self.config = config
        self.mqueue = q
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        cc = ClientConnect(self.client_address)
        cc.send(self.mqueue)
        while not cc.close:
            self.handle_request(cc)
        cd = ClientDisconnect(cc)
        cd.send(self.mqueue)
        self.finish()

    def handle_request(self, cc):
        server, request, err = None, None, None
        try:
            try:
                request = self.read_request(cc)
            except IOError, v:
                raise IOError, "Reading request: %s"%v
            if request is None:
                cc.close = True
                return
            cc.requestcount += 1
            request = request.send(self.mqueue)
            if request is None:
                cc.close = True
                return

            if request.is_response():
                response = request
                request = False
                response = response.send(self.mqueue)
            else:
                server = ServerConnection(request)
                server.send_request(request)
                try:
                    response = server.read_response()
                except IOError, v:
                    raise IOError, "Reading response: %s"%v
                response = response.send(self.mqueue)
                if response is None:
                    server.terminate()
            if response is None:
                cc.close = True
                return
            self.send_response(response)
        except IOError, v:
            cc.connection_error = v
            cc.close = True
        except ProxyError, e:
            cc.close = True
            cc.connection_error = "%s: %s"%(e.code, e.msg)
            if request:
                err = Error(request, e.msg)
                err.send(self.mqueue)
                self.send_error(e.code, e.msg)
        if server:
            server.terminate()

    def find_cert(self, host):
        if self.config.certfile:
            return self.config.certfile
        else:
            ret = utils.dummy_cert(self.config.certdir, self.config.cacert, host)
            time.sleep(self.config.cert_wait_time)
            if not ret:
                raise ProxyError(400, "mitmproxy: Unable to generate dummy cert.")
            return ret

    def read_request(self, client_conn):
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            return None
        method, scheme, host, port, path, httpminor = parse_request_line(line)
        if method == "CONNECT":
            # Discard additional headers sent to the proxy. Should I expose
            # these to users?
            while 1:
                d = self.rfile.readline()
                if d == '\r\n' or d == '\n':
                    break
            self.wfile.write(
                        'HTTP/1.1 200 Connection established\r\n' +
                        ('Proxy-agent: %s\r\n'%NAME) +
                        '\r\n'
                        )
            self.wfile.flush()
            kwargs = dict(
                certfile = self.find_cert(host),
                keyfile = self.config.certfile or self.config.cacert,
                server_side = True,
                ssl_version = ssl.PROTOCOL_SSLv23,
                do_handshake_on_connect = True
            )
            if sys.version_info[1] > 6:
                kwargs["ciphers"] = self.config.ciphers
            self.connection = ssl.wrap_socket(self.connection, **kwargs)
            self.rfile = FileLike(self.connection)
            self.wfile = FileLike(self.connection)
            method, scheme, host, port, path, httpminor = parse_request_line(self.rfile.readline())
        if scheme is None:
            scheme = "https"
        headers = utils.Headers()
        headers.read(self.rfile)
        if host is None and "host" in headers:
            netloc = headers["host"][0]
            if ':' in netloc:
                host, port = string.split(netloc, ':')
                port = int(port)
            else:
                host = netloc
                if scheme == "https":
                    port = 443
                else:
                    port = 80
            port = int(port)
        if host is None:
            raise ProxyError(400, 'Invalid request: %s'%request)
        if "expect" in headers:
            expect = ",".join(headers['expect'])
            if expect == "100-continue" and httpminor >= 1:
                self.wfile.write('HTTP/1.1 100 Continue\r\n')
                self.wfile.write('Proxy-agent: %s\r\n'%NAME)
                self.wfile.write('\r\n')
                del headers['expect']
            else:
                raise ProxyError(417, 'Unmet expect: %s'%expect)
        if httpminor == 0:
            client_conn.close = True
        if "connection" in headers:
            for value in ",".join(headers['connection']).split(","):
                value = value.strip()
                if value == "close":
                    client_conn.close = True
                if value == "keep-alive":
                    client_conn.close = False
        content = read_http_body(self.rfile, client_conn, headers, False)
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
            self.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
            self.wfile.write("Server: %s\r\n"%NAME)
            self.wfile.write("Connection: close\r\n")
            self.wfile.write("Content-type: text/html\r\n")
            self.wfile.write("\r\n")
            self.wfile.write('<html><head>\n<title>%d %s</title>\n</head>\n'
                    '<body>\n%s\n</body>\n</html>' % (code, response, body))
            self.wfile.flush()
        except:
            pass


class ProxyServerError(Exception): pass

ServerBase = SocketServer.ThreadingTCPServer
ServerBase.daemon_threads = True        # Terminate workers when main thread terminates
class ProxyServer(ServerBase):
    request_queue_size = 20
    allow_reuse_address = True
    def __init__(self, config, port, address=''):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config, self.port, self.address = config, port, address
        try:
            ServerBase.__init__(self, (address, port), ProxyHandler)
        except socket.error, v:
            raise ProxyServerError('Error starting proxy server: ' + v.strerror)
        self.masterq = None
        self.certdir = tempfile.mkdtemp(prefix="mitmproxy")
        config.certdir = self.certdir

    def set_mqueue(self, q):
        self.masterq = q

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(self.config, request, client_address, self, self.masterq)

    def shutdown(self):
        shutil.rmtree(self.certdir)
        ServerBase.shutdown(self)


# Command-line utils
def certificate_option_group(parser):
    group = optparse.OptionGroup(parser, "SSL")
    group.add_option(
        "--cert", action="store",
        type = "str", dest="cert", default=None,
        help = "User-created SSL certificate file."
    )
    group.add_option(
        "--ciphers", action="store",
        type = "str", dest="ciphers", default=None,
        help = "SSL ciphers."
    )
    parser.add_option_group(group)


def process_certificate_option_group(parser, options):
    conf = {}
    if options.cert:
        options.cert = os.path.expanduser(options.cert)
        if not os.path.exists(options.cert):
            parser.error("Manually created certificate does not exist: %s"%options.cert)

    cacert = os.path.join(options.confdir, "mitmproxy-ca.pem")
    cacert = os.path.expanduser(cacert)
    if not os.path.exists(cacert):
        utils.dummy_ca(cacert)
    if getattr(options, "cache", None) is not None:
        options.cache = os.path.expanduser(options.cache)
    return SSLConfig(
        certfile = options.cert,
        cacert = cacert,
        ciphers = options.ciphers,
        cert_wait_time = options.cert_wait_time
    )
