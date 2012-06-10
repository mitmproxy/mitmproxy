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
import utils, flow, certutils, version, wsgi


class ProxyError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class ProxyConfig:
    def __init__(self, certfile = None, ciphers = None, cacert = None, clientcerts = None, cert_wait_time=0, upstream_cert=False, body_size_limit = None, reverse_proxy=None):
        self.certfile = certfile
        self.ciphers = ciphers
        self.cacert = cacert
        self.clientcerts = clientcerts
        self.certdir = None
        self.cert_wait_time = cert_wait_time
        self.upstream_cert = upstream_cert
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


def read_http_body(rfile, client_conn, headers, all, limit):
    if 'transfer-encoding' in headers:
        if not ",".join(headers["transfer-encoding"]).lower() == "chunked":
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
        client_conn.close = True
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


def should_connection_close(httpversion, headers):
    """
        Checks the HTTP version and headers to see if this connection should be
        closed.
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


def read_http_body_request(rfile, wfile, client_conn, headers, httpversion, limit):
    if "expect" in headers:
        # FIXME: Should be forwarded upstream
        expect = ",".join(headers['expect'])
        if expect == "100-continue" and httpversion >= (1, 1):
            wfile.write('HTTP/1.1 100 Continue\r\n')
            wfile.write('Proxy-agent: %s\r\n'%version.NAMEVERSION)
            wfile.write('\r\n')
            del headers['expect']
    return read_http_body(rfile, client_conn, headers, False, limit)


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

    def readline(self, size = None):
        result = ''
        bytes_read = 0
        while True:
            if size is not None and bytes_read >= size:
                break
            ch = self.read(1)
            bytes_read += 1
            if not ch:
                break
            else:
                result += ch
                if ch == '\n':
                    break
        return result


class RequestReplayThread(threading.Thread):
    def __init__(self, config, flow, masterq):
        self.config, self.flow, self.masterq = config, flow, masterq
        threading.Thread.__init__(self)

    def run(self):
        try:
            r = self.flow.request
            server = ServerConnection(self.config, r.scheme, r.host, r.port)
            server.send(r)
            response = server.read_response(r)
            response._send(self.masterq)
        except ProxyError, v:
            err = flow.Error(self.flow.request, v.msg)
            err._send(self.masterq)


class ServerConnection:
    def __init__(self, config, scheme, host, port):
        self.config, self.scheme, self.host, self.port = config, scheme, host, port
        self.cert = None
        self.sock, self.rfile, self.wfile = None, None, None
        self.connect()
        self.requestcount = 0

    def connect(self):
        try:
            addr = socket.gethostbyname(self.host)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.scheme == "https":
                if self.config.clientcerts:
                    clientcert = os.path.join(self.config.clientcerts, self.host) + ".pem"
                    if not os.path.exists(clientcert):
                        clientcert = None
                else:
                    clientcert = None
                server = ssl.wrap_socket(server, certfile = clientcert)
            server.connect((addr, self.port))
            if self.scheme == "https":
                self.cert = server.getpeercert(True)
        except socket.error, err:
            raise ProxyError(502, 'Error connecting to "%s": %s' % (self.host, err))
        self.sock = server
        self.rfile, self.wfile = server.makefile('rb'), server.makefile('wb')

    def send(self, request):
        self.requestcount += 1
        try:
            d = request._assemble()
            if not d:
                raise ProxyError(502, "Incomplete request could not not be readied for transmission.")
            self.wfile.write(d)
            self.wfile.flush()
        except socket.error, err:
            raise ProxyError(502, 'Error sending data to "%s": %s' % (request.host, err))

    def read_response(self, request):
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
        httpversion = parse_http_protocol(proto)
        if httpversion is None:
            raise ProxyError(502, "Invalid HTTP version: %s."%httpversion)
        try:
            code = int(code)
        except ValueError:
            raise ProxyError(502, "Invalid server response: %s."%line)
        headers = read_headers(self.rfile)
        if code >= 100 and code <= 199:
            return self.read_response()
        if request.method == "HEAD" or code == 204 or code == 304:
            content = ""
        else:
            content = read_http_body(self.rfile, self, headers, True, self.config.body_size_limit)
        return flow.Response(request, httpversion, code, msg, headers, content, self.cert)

    def terminate(self):
        try:
            if not self.wfile.closed:
                self.wfile.flush()
            self.sock.close()
        except IOError:
            pass


class ProxyHandler(SocketServer.StreamRequestHandler):
    def __init__(self, config, request, client_address, server, q):
        self.mqueue = q
        self.config = config
        self.server_conn = None
        self.proxy_connect_state = None
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        cc = flow.ClientConnect(self.client_address)
        cc._send(self.mqueue)
        while self.handle_request(cc) and not cc.close:
            pass
        cc.close = True
        cd = flow.ClientDisconnect(cc)
        cd._send(self.mqueue)
        self.finish()

    def server_connect(self, scheme, host, port):
        sc = self.server_conn
        if sc and (scheme, host, port) != (sc.scheme, sc.host, sc.port):
            sc.terminate()
            self.server_conn = None
        if not self.server_conn:
            self.server_conn = ServerConnection(self.config, scheme, host, port)

    def handle_request(self, cc):
        try:
            request, err = None, None
            try:
                request = self.read_request(cc)
            except IOError, v:
                raise IOError, "Reading request: %s"%v
            if request is None:
                return
            cc.requestcount += 1

            app = self.server.apps.get(request)
            if app:
                app.serve(request, self.wfile)
            else:
                request = request._send(self.mqueue)
                if request is None:
                    return

                if isinstance(request, flow.Response):
                    response = request
                    request = False
                    response = response._send(self.mqueue)
                else:
                    if self.config.reverse_proxy:
                        scheme, host, port = self.config.reverse_proxy
                    else:
                        scheme, host, port = request.scheme, request.host, request.port
                    self.server_connect(scheme, host, port)
                    self.server_conn.send(request)
                    try:
                        response = self.server_conn.read_response(request)
                    except IOError, v:
                        raise IOError, "Reading response: %s"%v
                    response = response._send(self.mqueue)
                    if response is None:
                        self.server_conn.terminate()
                if response is None:
                    return
                self.send_response(response)
                if should_connection_close(request.httpversion, request.headers):
                    return
        except IOError, v:
            cc.connection_error = v
        except ProxyError, e:
            cc.connection_error = "%s: %s"%(e.code, e.msg)
            if request:
                err = flow.Error(request, e.msg)
                err._send(self.mqueue)
                self.send_error(e.code, e.msg)
        else:
            return True

    def find_cert(self, host, port):
        if self.config.certfile:
            return self.config.certfile
        else:
            sans = []
            if self.config.upstream_cert:
                cert = certutils.get_remote_cert(host, port)
                sans = cert.altnames
                host = cert.cn
            ret = certutils.dummy_cert(self.config.certdir, self.config.cacert, host, sans)
            time.sleep(self.config.cert_wait_time)
            if not ret:
                raise ProxyError(502, "mitmproxy: Unable to generate dummy cert.")
            return ret

    def convert_to_ssl(self, cert):
        kwargs = dict(
            certfile = cert,
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

    def read_request(self, client_conn):
        line = self.rfile.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = self.rfile.readline()
        if line == "":
            return None

        if self.config.reverse_proxy:
            scheme, host, port = self.config.reverse_proxy
            method, path, httpversion = parse_init_http(line)
            headers = read_headers(self.rfile)
            content = read_http_body_request(
                        self.rfile, self.wfile, client_conn, headers, httpversion, self.config.body_size_limit
                    )
            return flow.Request(client_conn, httpversion, host, port, "http", method, path, headers, content)
        else:
            if line.startswith("CONNECT"):
                host, port, httpversion = parse_init_connect(line)
                # FIXME: Discard additional headers sent to the proxy. Should I expose
                # these to users?
                while 1:
                    d = self.rfile.readline()
                    if d == '\r\n' or d == '\n':
                        break
                self.wfile.write(
                            'HTTP/1.1 200 Connection established\r\n' +
                            ('Proxy-agent: %s\r\n'%version.NAMEVERSION) +
                            '\r\n'
                            )
                self.wfile.flush()
                certfile = self.find_cert(host, port)
                self.convert_to_ssl(certfile)
                self.proxy_connect_state = (host, port, httpversion)
                line = self.rfile.readline(line)

            if self.proxy_connect_state:
                host, port, httpversion = self.proxy_connect_state
                method, path, httpversion = parse_init_http(line)
                headers = read_headers(self.rfile)
                content = read_http_body_request(
                    self.rfile, self.wfile, client_conn, headers, httpversion, self.config.body_size_limit
                )
                return flow.Request(client_conn, httpversion, host, port, "https", method, path, headers, content)
            else:
                method, scheme, host, port, path, httpversion = parse_init_proxy(line)
                headers = read_headers(self.rfile)
                content = read_http_body_request(
                    self.rfile, self.wfile, client_conn, headers, httpversion, self.config.body_size_limit
                )
                return flow.Request(client_conn, httpversion, host, port, scheme, method, path, headers, content)

    def send_response(self, response):
        d = response._assemble()
        if not d:
            raise ProxyError(502, "Incomplete response could not not be readied for transmission.")
        self.wfile.write(d)
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
            self.wfile.write("Server: %s\r\n"%version.NAMEVERSION)
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
    bound = True
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
        self.apps = wsgi.AppRegistry()

    def start_slave(self, klass, masterq):
        slave = klass(masterq, self)
        slave.start()

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


class DummyServer:
    bound = False
    def __init__(self, config):
        self.config = config

    def start_slave(self, klass, masterq):
        pass

    def shutdown(self):
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
    group.add_option(
        "--client-certs", action="store",
        type = "str", dest = "clientcerts", default=None,
        help = "Client certificate directory."
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
        certutils.dummy_ca(cacert)
    if getattr(options, "cache", None) is not None:
        options.cache = os.path.expanduser(options.cache)
    body_size_limit = utils.parse_size(options.body_size_limit)

    if options.reverse_proxy:
        rp = utils.parse_proxy_spec(options.reverse_proxy)
        if not rp:
            parser.error("Invalid reverse proxy specification: %s"%options.reverse_proxy)
    else:
        rp = None

    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts) or not os.path.isdir(options.clientcerts):
            parser.error("Client certificate directory does not exist or is not a directory: %s"%options.clientcerts)

    return ProxyConfig(
        certfile = options.cert,
        cacert = cacert,
        clientcerts = options.clientcerts,
        ciphers = options.ciphers,
        cert_wait_time = options.cert_wait_time,
        body_size_limit = body_size_limit,
        upstream_cert = options.upstream_cert,
        reverse_proxy = rp
    )
