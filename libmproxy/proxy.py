# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    A simple proxy server implementation, which always reads all of a server
    response into memory, performs some transformation, and then writes it back
    to the client.
"""
import sys, os, string, socket, time
import shutil, tempfile, threading
import optparse, SocketServer, ssl
import utils, flow

NAME = "mitmproxy"


class ProxyError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class ProxyConfig:
    def __init__(self, certfile = None, ciphers = None, cacert = None, cert_wait_time=0, body_size_limit = None, reverse_proxy=None):
        self.certfile = certfile
        self.ciphers = ciphers
        self.cacert = cacert
        self.certdir = None
        self.cert_wait_time = cert_wait_time
        self.body_size_limit = body_size_limit
        self.reverse_proxy = reverse_proxy


def read_headers(fp):
    """
        Read a set of headers from a file pointer. Stop once a blank line
        is reached. Return a ODict object.
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
            raise ProxyError(400, "Invalid chunked encoding length: %s"%line)
        if not length:
            break
        total += length
        if limit is not None and total > limit:
            msg = "HTTP Body too large."\
                  " Limit is %s, chunked content length was at least %s"%(limit, total)
            raise ProxyError(509, msg)
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


def read_http_body(rfile, connection, headers, all, limit):
    if 'transfer-encoding' in headers:
        if not ",".join(headers["transfer-encoding"]) == "chunked":
            raise IOError('Invalid transfer-encoding')
        content = read_chunked(rfile, limit)
    elif "content-length" in headers:
        try:
            l = int(headers["content-length"][0])
        except ValueError:
            # FIXME: Not strictly correct - this could be from the server, in which
            # case we should send a 502.
            raise ProxyError(400, "Invalid content-length header: %s"%headers["content-length"])
        if limit is not None and l > limit:
            raise ProxyError(509, "HTTP Body too large. Limit is %s, content-length was %s"%(limit, l))
        content = rfile.read(l)
    elif all:
        content = rfile.read(limit if limit else None)
        connection.close = True
    else:
        content = ""
    return content


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
            parts = utils.parse_url(url)
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
class RequestReplayThread(threading.Thread):
    def __init__(self, config, flow, masterq):
        self.config, self.flow, self.masterq = config, flow, masterq
        threading.Thread.__init__(self)

    def run(self):
        try:
            server = ServerConnection(self.config, self.flow.request)
            server.send()
            response = server.read_response()
            response._send(self.masterq)
        except ProxyError, v:
            err = flow.Error(self.flow.request, v.msg)
            err._send(self.masterq)


class ServerConnection:
    def __init__(self, config, request):
        self.config, self.request = config, request
        if config.reverse_proxy:
            self.scheme, self.host, self.port = config.reverse_proxy
        else:
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
            raise ProxyError(502, 'Error connecting to "%s": %s' % (self.host, err))
        self.server = server
        self.rfile, self.wfile = server.makefile('rb'), server.makefile('wb')

    def send(self):
        self.request.close = self.close
        try:
            self.wfile.write(self.request._assemble())
            self.wfile.flush()
        except socket.error, err:
            raise ProxyError(502, 'Error sending data to "%s": %s' % (self.request.host, err))

    def read_response(self):
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if not line:
            raise ProxyError(502, "Blank server response.")
        parts = line.strip().split(" ", 2)
        if len(parts) == 2: # handle missing message gracefully
            parts.append("")
        if not len(parts) == 3:
            raise ProxyError(502, "Invalid server response: %s."%line)
        proto, code, msg = parts
        try:
            code = int(code)
        except ValueError:
            raise ProxyError(502, "Invalid server response: %s."%line)
        headers = read_headers(self.rfile)
        if code >= 100 and code <= 199:
            return self.read_response()
        if self.request.method == "HEAD" or code == 204 or code == 304:
            content = ""
        else:
            content = read_http_body(self.rfile, self, headers, True, self.config.body_size_limit)
        return flow.Response(self.request, code, msg, headers, content)

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
        cc = flow.ClientConnect(self.client_address)
        cc._send(self.mqueue)
        while not cc.close:
            self.handle_request(cc)
        cd = flow.ClientDisconnect(cc)
        cd._send(self.mqueue)
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
            request = request._send(self.mqueue)
            if request is None:
                cc.close = True
                return

            if isinstance(request, flow.Response):
                response = request
                request = False
                response = response._send(self.mqueue)
            else:
                server = ServerConnection(self.config, request)
                server.send()
                try:
                    response = server.read_response()
                except IOError, v:
                    raise IOError, "Reading response: %s"%v
                response = response._send(self.mqueue)
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
                err = flow.Error(request, e.msg)
                err._send(self.mqueue)
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
                raise ProxyError(502, "mitmproxy: Unable to generate dummy cert.")
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
                do_handshake_on_connect = True,
            )
            if sys.version_info[1] > 6:
                kwargs["ciphers"] = self.config.ciphers
            self.connection = ssl.wrap_socket(self.connection, **kwargs)
            self.rfile = FileLike(self.connection)
            self.wfile = FileLike(self.connection)
            method, scheme, host, port, path, httpminor = parse_request_line(self.rfile.readline())
        if scheme is None:
            scheme = "https"
        headers = read_headers(self.rfile)
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
            if self.config.reverse_proxy:
                scheme, host, port = self.config.reverse_proxy
            else:
                # FIXME: We only specify the first part of the invalid request in this error.
                # We should gather up everything read from the socket, and specify it all.
                raise ProxyError(400, 'Invalid request: %s'%line)
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
        content = read_http_body(self.rfile, client_conn, headers, False, self.config.body_size_limit)
        return flow.Request(client_conn, host, port, scheme, method, path, headers, content)

    def send_response(self, response):
        self.wfile.write(response._assemble())
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
        ServerBase.shutdown(self)
        try:
            shutil.rmtree(self.certdir)
        except OSError:
            pass


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


def process_proxy_options(parser, options):
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
    body_size_limit = utils.parse_size(options.body_size_limit)

    if options.reverse_proxy:
        rp = utils.parse_proxy_spec(options.reverse_proxy)
        if not rp:
            parser.error("Invalid reverse proxy specification: %s"%options.reverse_proxy)
    else:
        rp = None

    return ProxyConfig(
        certfile = options.cert,
        cacert = cacert,
        ciphers = options.ciphers,
        cert_wait_time = options.cert_wait_time,
        body_size_limit = body_size_limit,
        reverse_proxy = rp
    )
