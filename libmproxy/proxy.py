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
import sys, os, string, socket, time
import shutil, tempfile, threading
import SocketServer
from OpenSSL import SSL
from netlib import odict, tcp, http, wsgi, certutils, http_status
import utils, flow, version, platform, controller


class ProxyError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class Log(controller.Msg):
    def __init__(self, msg):
        controller.Msg.__init__(self)
        self.msg = msg



class ProxyConfig:
    def __init__(self, certfile = None, cacert = None, clientcerts = None, cert_wait_time=0, no_upstream_cert=False, body_size_limit = None, reverse_proxy=None, transparent_proxy=None, certdir = None):
        assert not (reverse_proxy and transparent_proxy)
        self.certfile = certfile
        self.cacert = cacert
        self.clientcerts = clientcerts
        self.certdir = certdir
        self.cert_wait_time = cert_wait_time
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.reverse_proxy = reverse_proxy
        self.transparent_proxy = transparent_proxy


class RequestReplayThread(threading.Thread):
    def __init__(self, config, flow, masterq):
        self.config, self.flow, self.masterq = config, flow, masterq
        threading.Thread.__init__(self)

    def run(self):
        try:
            r = self.flow.request
            server = ServerConnection(self.config, r.host, r.port)
            server.connect(r.scheme)
            server.send(r)
            httpversion, code, msg, headers, content = http.read_response(
                server.rfile, r.method, self.config.body_size_limit
            )
            response = flow.Response(
                self.flow.request, httpversion, code, msg, headers, content, server.cert
            )
            response._send(self.masterq)
        except (ProxyError, http.HttpError, tcp.NetLibError), v:
            err = flow.Error(self.flow.request, str(v))
            err._send(self.masterq)


class ServerConnection(tcp.TCPClient):
    def __init__(self, config, host, port):
        tcp.TCPClient.__init__(self, host, port)
        self.config = config
        self.requestcount = 0

    def connect(self, scheme):
        tcp.TCPClient.connect(self)
        if scheme == "https":
            clientcert = None
            if self.config.clientcerts:
                path = os.path.join(self.config.clientcerts, self.host) + ".pem"
                if os.path.exists(clientcert):
                    clientcert = path
            try:
                self.convert_to_ssl(clientcert=clientcert, sni=self.host)
            except tcp.NetLibError, v:
                raise ProxyError(400, str(v))

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

    def terminate(self):
        try:
            if not self.wfile.closed:
                self.wfile.flush()
            self.connection.close()
        except IOError:
            pass


class ProxyHandler(tcp.BaseHandler):
    def __init__(self, config, connection, client_address, server, mqueue, server_version):
        self.mqueue, self.server_version = mqueue, server_version
        self.config = config
        self.server_conn = None
        self.proxy_connect_state = None
        self.sni = None
        tcp.BaseHandler.__init__(self, connection, client_address, server)

    def handle(self):
        cc = flow.ClientConnect(self.client_address)
        self.log(cc, "connect")
        cc._send(self.mqueue)
        while self.handle_request(cc) and not cc.close:
            pass
        cc.close = True
        cd = flow.ClientDisconnect(cc)

        self.log(
            cc, "disconnect",
            [
                "handled %s requests"%cc.requestcount]
        )
        cd._send(self.mqueue)

    def server_connect(self, scheme, host, port):
        sc = self.server_conn
        if sc and (host, port) != (sc.host, sc.port):
            sc.terminate()
            self.server_conn = None
        if not self.server_conn:
            try:
                self.server_conn = ServerConnection(self.config, host, port)
                self.server_conn.connect(scheme)
            except tcp.NetLibError, v:
                raise ProxyError(502, v)

    def handle_request(self, cc):
        try:
            request, err = None, None
            request = self.read_request(cc)
            if request is None:
                return
            cc.requestcount += 1

            app = self.server.apps.get(request)
            if app:
                err = app.serve(request, self.wfile)
                if err:
                    self.log(cc, "Error in wsgi app.", err.split("\n"))
                    return
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
                    httpversion, code, msg, headers, content = http.read_response(
                        self.server_conn.rfile,
                        request.method,
                        self.config.body_size_limit
                    )
                    response = flow.Response(
                        request, httpversion, code, msg, headers, content, self.server_conn.cert
                    )
                    response = response._send(self.mqueue)
                    if response is None:
                        self.server_conn.terminate()
                if response is None:
                    return
                self.send_response(response)
                if request and http.request_connection_close(request.httpversion, request.headers):
                    return
                # We could keep the client connection when the server
                # connection needs to go away.  However, we want to mimic
                # behaviour as closely as possible to the client, so we
                # disconnect.
                if http.response_connection_close(response.httpversion, response.headers):
                    return
        except (IOError, ProxyError, http.HttpError, tcp.NetLibDisconnect), e:
            if hasattr(e, "code"):
                cc.error = "%s: %s"%(e.code, e.msg)
            else:
                cc.error = str(e)

            if request:
                err = flow.Error(request, cc.error)
                err._send(self.mqueue)
                self.log(
                    cc, cc.error,
                    ["url: %s"%request.get_url()]
                )
            else:
                self.log(cc, cc.error)

            if isinstance(e, ProxyError):
                self.send_error(e.code, e.msg)
        else:
            return True

    def log(self, cc, msg, subs=()):
        msg = [
            "%s:%s: "%cc.address + msg
        ]
        for i in subs:
            msg.append("  -> "+i)
        msg = "\n".join(msg)
        l = Log(msg)
        l._send(self.mqueue)

    def find_cert(self, host, port, sni):
        if self.config.certfile:
            return self.config.certfile
        else:
            sans = []
            if not self.config.no_upstream_cert:
                try:
                    cert = certutils.get_remote_cert(host, port, sni)
                except tcp.NetLibError, v:
                    raise ProxyError(502, "Unable to get remote cert: %s"%str(v))
                sans = cert.altnames
                host = cert.cn.decode("utf8").encode("idna")
            ret = certutils.dummy_cert(self.config.certdir, self.config.cacert, host, sans)
            time.sleep(self.config.cert_wait_time)
            if not ret:
                raise ProxyError(502, "mitmproxy: Unable to generate dummy cert.")
            return ret

    def get_line(self, fp):
        """
            Get a line, possibly preceded by a blank.
        """
        line = fp.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = fp.readline()
        return line

    def handle_sni(self, conn):
        sn = conn.get_servername()
        if sn:
            self.sni = sn.decode("utf8").encode("idna")

    def read_request(self, client_conn):
        if self.config.transparent_proxy:
            host, port = self.config.transparent_proxy["resolver"].original_addr(self.connection)
            if not self.ssl_established and (port in self.config.transparent_proxy["sslports"]):
                scheme = "https"
                certfile = self.find_cert(host, port, None)
                try:
                    self.convert_to_ssl(certfile, self.config.certfile or self.config.cacert)
                except tcp.NetLibError, v:
                    raise ProxyError(400, str(v))
            else:
                scheme = "http"
            host = self.sni or host
            line = self.get_line(self.rfile)
            if line == "":
                return None
            r = http.parse_init_http(line)
            if not r:
                raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
            method, path, httpversion = r
            headers = http.read_headers(self.rfile)
            if headers is None:
                raise ProxyError(400, "Invalid headers")
            content = http.read_http_body_request(
                        self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                    )
            return flow.Request(client_conn, httpversion, host, port, scheme, method, path, headers, content)
        elif self.config.reverse_proxy:
            line = self.get_line(self.rfile)
            if line == "":
                return None
            scheme, host, port = self.config.reverse_proxy
            r = http.parse_init_http(line)
            if not r:
                raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
            method, path, httpversion = r
            headers = http.read_headers(self.rfile)
            if headers is None:
                raise ProxyError(400, "Invalid headers")
            content = http.read_http_body_request(
                        self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                    )
            return flow.Request(client_conn, httpversion, host, port, "http", method, path, headers, content)
        else:
            line = self.get_line(self.rfile)
            if line == "":
                return None
            if line.startswith("CONNECT"):
                r = http.parse_init_connect(line)
                if not r:
                    raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
                host, port, httpversion = r
                # FIXME: Discard additional headers sent to the proxy. Should I expose
                # these to users?
                while 1:
                    d = self.rfile.readline()
                    if d == '\r\n' or d == '\n':
                        break
                self.wfile.write(
                            'HTTP/1.1 200 Connection established\r\n' +
                            ('Proxy-agent: %s\r\n'%self.server_version) +
                            '\r\n'
                            )
                self.wfile.flush()
                certfile = self.find_cert(host, port, None)
                try:
                    self.convert_to_ssl(certfile, self.config.certfile or self.config.cacert)
                except tcp.NetLibError, v:
                    raise ProxyError(400, str(v))
                self.proxy_connect_state = (host, port, httpversion)
                line = self.rfile.readline(line)
            if self.proxy_connect_state:
                host, port, httpversion = self.proxy_connect_state
                r = http.parse_init_http(line)
                if not r:
                    raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
                method, path, httpversion = r
                headers = http.read_headers(self.rfile)
                if headers is None:
                    raise ProxyError(400, "Invalid headers")
                content = http.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                )
                display_host = headers['Host'][0] if 'Host' in headers else host
                return flow.Request(client_conn, httpversion, display_host, port, "https", method, path, headers, content)
            else:
                r = http.parse_init_proxy(line)
                if not r:
                    raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
                method, scheme, host, port, path, httpversion = http.parse_init_proxy(line)
                headers = http.read_headers(self.rfile)
                if headers is None:
                    raise ProxyError(400, "Invalid headers")
                content = http.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                )
                return flow.Request(client_conn, httpversion, host, port, scheme, method, path, headers, content)

    def send_response(self, response):
        d = response._assemble()
        if not d:
            raise ProxyError(502, "Incomplete response could not not be readied for transmission.")
        self.wfile.write(d)
        self.wfile.flush()

    def send_error(self, code, body):
        try:
            response = http_status.RESPONSES.get(code, "Unknown")
            self.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
            self.wfile.write("Server: %s\r\n"%self.server_version)
            self.wfile.write("Connection: close\r\n")
            self.wfile.write("Content-type: text/html\r\n")
            self.wfile.write("\r\n")
            self.wfile.write('<html><head>\n<title>%d %s</title>\n</head>\n'
                    '<body>\n%s\n</body>\n</html>' % (code, response, body))
            self.wfile.flush()
        except:
            pass


class ProxyServerError(Exception): pass


class ProxyServer(tcp.TCPServer):
    allow_reuse_address = True
    bound = True
    def __init__(self, config, port, address='', server_version=version.NAMEVERSION):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config, self.port, self.address = config, port, address
        self.server_version = server_version
        try:
            tcp.TCPServer.__init__(self, (address, port))
        except socket.error, v:
            raise ProxyServerError('Error starting proxy server: ' + v.strerror)
        self.masterq = None
        if config.certdir:
            self.certdir = config.certdir
            self.remove_certdir = False
        else:
            self.certdir = tempfile.mkdtemp(prefix="mitmproxy")
            config.certdir = self.certdir
            self.remove_certdir = True
        self.apps = AppRegistry()

    def start_slave(self, klass, masterq):
        slave = klass(masterq, self)
        slave.start()

    def set_mqueue(self, q):
        self.masterq = q

    def handle_connection(self, request, client_address):
        h = ProxyHandler(self.config, request, client_address, self, self.masterq, self.server_version)
        h.handle()
        try:
            h.finish()
        except tcp.NetLibDisconnect, e:
            pass

    def handle_shutdown(self):
        try:
            if self.remove_certdir:
                shutil.rmtree(self.certdir)
        except OSError:
            pass


class AppRegistry:
    def __init__(self):
        self.apps = {}

    def add(self, app, domain, port):
        """
            Add a WSGI app to the registry, to be served for requests to the
            specified domain, on the specified port.
        """
        self.apps[(domain, port)] = wsgi.WSGIAdaptor(app, domain, port, version.NAMEVERSION)

    def get(self, request):
        """
            Returns an WSGIAdaptor instance if request matches an app, or None.
        """
        if (request.host, request.port) in self.apps:
            return self.apps[(request.host, request.port)]
        if "host" in request.headers:
            host = request.headers["host"][0]
            return self.apps.get((host, request.port), None)


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
    group = parser.add_argument_group("SSL")
    group.add_argument(
        "--cert", action="store",
        type = str, dest="cert", default=None,
        help = "User-created SSL certificate file."
    )
    group.add_argument(
        "--client-certs", action="store",
        type = str, dest = "clientcerts", default=None,
        help = "Client certificate directory."
    )
    group.add_argument(
        "--dummy-certs", action="store",
        type = str, dest = "certdir", default=None,
        help = "Generated dummy certs directory."
    )


TRANSPARENT_SSL_PORTS = [443, 8443]

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

    if options.reverse_proxy and options.transparent_proxy:
        parser.errror("Can't set both reverse proxy and transparent proxy.")

    if options.transparent_proxy:
        if not platform.resolver:
            parser.error("Transparent mode not supported on this platform.")
        trans = dict(
            resolver = platform.resolver(),
            sslports = TRANSPARENT_SSL_PORTS
        )
    else:
        trans = None

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

    if options.certdir:
        options.certdir = os.path.expanduser(options.certdir)
        if not os.path.exists(options.certdir) or not os.path.isdir(options.certdir):
            parser.error("Dummy cert directory does not exist or is not a directory: %s"%options.certdir)

    return ProxyConfig(
        certfile = options.cert,
        cacert = cacert,
        clientcerts = options.clientcerts,
        cert_wait_time = options.cert_wait_time,
        body_size_limit = body_size_limit,
        no_upstream_cert = options.no_upstream_cert,
        reverse_proxy = rp,
        transparent_proxy = trans,
        certdir = options.certdir
    )
