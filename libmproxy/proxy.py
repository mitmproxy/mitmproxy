import sys, os, string, socket, time
import shutil, tempfile, threading
import SocketServer
from OpenSSL import SSL
from netlib import odict, tcp, http, wsgi, certutils, http_status, http_auth
import utils, flow, version, platform, controller


KILL = 0


class ProxyError(Exception):
    def __init__(self, code, msg, headers=None):
        self.code, self.msg, self.headers = code, msg, headers

    def __str__(self):
        return "ProxyError(%s, %s)"%(self.code, self.msg)


class Log:
    def __init__(self, msg):
        self.msg = msg


class ProxyConfig:
    def __init__(self, certfile = None, cacert = None, clientcerts = None, no_upstream_cert=False, body_size_limit = None, reverse_proxy=None, transparent_proxy=None, authenticator=None):
        self.certfile = certfile
        self.cacert = cacert
        self.clientcerts = clientcerts
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.reverse_proxy = reverse_proxy
        self.transparent_proxy = transparent_proxy
        self.authenticator = authenticator
        self.certstore = certutils.CertStore()


class ServerConnection(tcp.TCPClient):
    def __init__(self, config, scheme, host, port, sni):
        tcp.TCPClient.__init__(self, host, port)
        self.config = config
        self.scheme, self.sni = scheme, sni
        self.requestcount = 0
        self.tcp_setup_timestamp = None
        self.ssl_setup_timestamp = None

    def connect(self):
        tcp.TCPClient.connect(self)
        self.tcp_setup_timestamp = time.time()
        if self.scheme == "https":
            clientcert = None
            if self.config.clientcerts:
                path = os.path.join(self.config.clientcerts, self.host.encode("idna")) + ".pem"
                if os.path.exists(path):
                    clientcert = path
            try:
                self.convert_to_ssl(cert=clientcert, sni=self.sni)
                self.ssl_setup_timestamp = time.time()
            except tcp.NetLibError, v:
                raise ProxyError(400, str(v))

    def send(self, request):
        self.requestcount += 1
        d = request._assemble()
        if not d:
            raise ProxyError(502, "Cannot transmit an incomplete request.")
        self.wfile.write(d)
        self.wfile.flush()

    def terminate(self):
        if self.connection:
            try:
                self.wfile.flush()
            except tcp.NetLibDisconnect: # pragma: no cover
                pass
            self.connection.close()



class RequestReplayThread(threading.Thread):
    def __init__(self, config, flow, masterq):
        self.config, self.flow, self.channel = config, flow, controller.Channel(masterq)
        threading.Thread.__init__(self)

    def run(self):
        try:
            r = self.flow.request
            server = ServerConnection(self.config, r.scheme, r.host, r.port, r.host)
            server.connect()
            server.send(r)
            tsstart = utils.timestamp()
            httpversion, code, msg, headers, content = http.read_response(
                server.rfile, r.method, self.config.body_size_limit
            )
            response = flow.Response(
                self.flow.request, httpversion, code, msg, headers, content, server.cert, 
                server.rfile.first_byte_timestamp
            )
            self.channel.ask(response)
        except (ProxyError, http.HttpError, tcp.NetLibError), v:
            err = flow.Error(self.flow.request, str(v))
            self.channel.ask(err)


class HandleSNI:
    def __init__(self, handler, client_conn, host, port, cert, key):
        self.handler, self.client_conn, self.host, self.port = handler, client_conn, host, port
        self.cert, self.key = cert, key

    def __call__(self, connection):
        try:
            sn = connection.get_servername()
            if sn:
                self.handler.get_server_connection(self.client_conn, "https", self.host, self.port, sn)
                new_context = SSL.Context(SSL.TLSv1_METHOD)
                new_context.use_privatekey_file(self.key)
                new_context.use_certificate(self.cert.x509)
                connection.set_context(new_context)
                self.handler.sni = sn.decode("utf8").encode("idna")
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except Exception, e: # pragma: no cover
            pass


class ProxyHandler(tcp.BaseHandler):
    def __init__(self, config, connection, client_address, server, channel, server_version):
        self.channel, self.server_version = channel, server_version
        self.config = config
        self.proxy_connect_state = None
        self.sni = None
        self.server_conn = None
        tcp.BaseHandler.__init__(self, connection, client_address, server)

    def get_server_connection(self, cc, scheme, host, port, sni):
        """
            When SNI is in play, this means we have an SSL-encrypted
            connection, which means that the entire handler is dedicated to a
            single server connection - no multiplexing. If this assumption ever
            breaks, we'll have to do something different with the SNI host
            variable on the handler object.
        """
        sc = self.server_conn
        if not sni:
            sni = host
        if sc and (scheme, host, port, sni) != (sc.scheme, sc.host, sc.port, sc.sni):
            sc.terminate()
            self.server_conn = None
            self.log(
                cc,
                "switching connection", [
                    "%s://%s:%s (sni=%s) -> %s://%s:%s (sni=%s)"%(
                        scheme, host, port, sni,
                        sc.scheme, sc.host, sc.port, sc.sni
                    )
                ]
            )
        if not self.server_conn:
            try:
                self.server_conn = ServerConnection(self.config, scheme, host, port, sni)
                self.server_conn.connect()
            except tcp.NetLibError, v:
                raise ProxyError(502, v)
        return self.server_conn

    def del_server_connection(self):
        if self.server_conn:
            self.server_conn.terminate()
        self.server_conn = None

    def handle(self):
        cc = flow.ClientConnect(self.client_address)
        self.log(cc, "connect")
        self.channel.ask(cc)
        while self.handle_request(cc) and not cc.close:
            pass
        cc.close = True
        self.del_server_connection()

        cd = flow.ClientDisconnect(cc)
        self.log(
            cc, "disconnect",
            [
                "handled %s requests"%cc.requestcount]
        )
        self.channel.tell(cd)

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
                request_reply = self.channel.ask(request)
                if request_reply is None or request_reply == KILL:
                    return
                elif isinstance(request_reply, flow.Response):
                    request = False
                    response = request_reply
                    response_reply = self.channel.ask(response)
                else:
                    request = request_reply
                    if self.config.reverse_proxy:
                        scheme, host, port = self.config.reverse_proxy
                    else:
                        scheme, host, port = request.scheme, request.host, request.port

                    # If we've already pumped a request over this connection,
                    # it's possible that the server has timed out. If this is
                    # the case, we want to reconnect without sending an error
                    # to the client.
                    while 1:
                        sc = self.get_server_connection(cc, scheme, host, port, self.sni)
                        sc.send(request)
                        if sc.requestcount == 1: # add timestamps only for first request (others are not directly affected)
                            request.tcp_setup_timestamp = sc.tcp_setup_timestamp
                            request.ssl_setup_timestamp = sc.ssl_setup_timestamp
                        sc.rfile.reset_timestamps()
                        try:
                            tsstart = utils.timestamp()
                            httpversion, code, msg, headers, content = http.read_response(
                                sc.rfile,
                                request.method,
                                self.config.body_size_limit
                            )
                        except http.HttpErrorConnClosed, v:
                            self.del_server_connection()
                            if sc.requestcount > 1:
                                continue
                            else:
                                raise
                        except http.HttpError, v:
                            raise ProxyError(502, "Invalid server response.")
                        else:
                            break

                    response = flow.Response(
                        request, httpversion, code, msg, headers, content, sc.cert,
                        sc.rfile.first_byte_timestamp
                    )
                    response_reply = self.channel.ask(response)
                    # Not replying to the server invalidates the server
                    # connection, so we terminate.
                    if response_reply == KILL:
                        sc.terminate()

                if response_reply == KILL:
                    return
                else:
                    response = response_reply
                    self.send_response(response)
                    if request and http.request_connection_close(request.httpversion, request.headers):
                        return
                    # We could keep the client connection when the server
                    # connection needs to go away.  However, we want to mimic
                    # behaviour as closely as possible to the client, so we
                    # disconnect.
                    if http.response_connection_close(response.httpversion, response.headers):
                        return
        except (IOError, ProxyError, http.HttpError, tcp.NetLibError), e:
            if hasattr(e, "code"):
                cc.error = "%s: %s"%(e.code, e.msg)
            else:
                cc.error = str(e)

            if request:
                err = flow.Error(request, cc.error)
                self.channel.ask(err)
                self.log(
                    cc, cc.error,
                    ["url: %s"%request.get_url()]
                )
            else:
                self.log(cc, cc.error)
            if isinstance(e, ProxyError):
                self.send_error(e.code, e.msg, e.headers)
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
        self.channel.tell(l)

    def find_cert(self, cc, host, port, sni):
        if self.config.certfile:
            return certutils.SSLCert.from_pem(file(self.config.certfile, "r").read())
        else:
            sans = []
            if not self.config.no_upstream_cert:
                conn = self.get_server_connection(cc, "https", host, port, sni)
                sans = conn.cert.altnames
                host = conn.cert.cn.decode("utf8").encode("idna")
            ret = self.config.certstore.get_cert(host, sans, self.config.cacert)
            if not ret:
                raise ProxyError(502, "Unable to generate dummy cert.")
            return ret

    def get_line(self, fp):
        """
            Get a line, possibly preceded by a blank.
        """
        line = fp.readline()
        if line == "\r\n" or line == "\n": # Possible leftover from previous message
            line = fp.readline()
        return line

    def read_request_transparent(self, client_conn):
        orig = self.config.transparent_proxy["resolver"].original_addr(self.connection)
        if not orig:
            raise ProxyError(502, "Transparent mode failure: could not resolve original destination.")
        self.log(client_conn, "transparent to %s:%s"%orig)

        host, port = orig
        if port in self.config.transparent_proxy["sslports"]:
            scheme = "https"
            if not self.ssl_established:
                dummycert = self.find_cert(client_conn, host, port, host)
                sni = HandleSNI(
                    self, client_conn, host, port,
                    dummycert, self.config.certfile or self.config.cacert
                )
                try:
                    self.convert_to_ssl(dummycert, self.config.certfile or self.config.cacert, handle_sni=sni)
                except tcp.NetLibError, v:
                    raise ProxyError(400, str(v))
        else:
            scheme = "http"
        line = self.get_line(self.rfile)
        if line == "":
            return None
        r = http.parse_init_http(line)
        if not r:
            raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
        method, path, httpversion = r
        headers = self.read_headers(authenticate=False)
        content = http.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                )
        return flow.Request(
                    client_conn,httpversion, host, port, scheme, method, path, headers, content,
                    self.rfile.first_byte_timestamp, utils.timestamp()
               )

    def read_request_proxy(self, client_conn):
        line = self.get_line(self.rfile)
        if line == "":
            return None

        if not self.proxy_connect_state:
            connparts = http.parse_init_connect(line)
            if connparts:
                host, port, httpversion = connparts
                headers = self.read_headers(authenticate=True)
                self.wfile.write(
                            'HTTP/1.1 200 Connection established\r\n' +
                            ('Proxy-agent: %s\r\n'%self.server_version) +
                            '\r\n'
                            )
                self.wfile.flush()
                dummycert = self.find_cert(client_conn, host, port, host)
                sni = HandleSNI(
                    self, client_conn, host, port,
                    dummycert, self.config.certfile or self.config.cacert
                )
                try:
                    self.convert_to_ssl(dummycert, self.config.certfile or self.config.cacert, handle_sni=sni)
                except tcp.NetLibError, v:
                    raise ProxyError(400, str(v))
                self.proxy_connect_state = (host, port, httpversion)
                line = self.rfile.readline(line)

        if self.proxy_connect_state:
            r = http.parse_init_http(line)
            if not r:
                raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
            method, path, httpversion = r
            headers = self.read_headers(authenticate=False)

            host, port, _ = self.proxy_connect_state
            content = http.read_http_body_request(
                self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
            )
            return flow.Request(
                        client_conn, httpversion, host, port, "https", method, path, headers, content,
                        self.rfile.first_byte_timestamp, utils.timestamp()
                   )
        else:
            r = http.parse_init_proxy(line)
            if not r:
                raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
            method, scheme, host, port, path, httpversion = r
            headers = self.read_headers(authenticate=True)
            content = http.read_http_body_request(
                self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
            )
            return flow.Request(
                        client_conn, httpversion, host, port, scheme, method, path, headers, content,
                        self.rfile.first_byte_timestamp, utils.timestamp()
                    )

    def read_request_reverse(self, client_conn):
        line = self.get_line(self.rfile)
        if line == "":
            return None
        scheme, host, port = self.config.reverse_proxy
        r = http.parse_init_http(line)
        if not r:
            raise ProxyError(400, "Bad HTTP request line: %s"%repr(line))
        method, path, httpversion = r
        headers = self.read_headers(authenticate=False)
        content = http.read_http_body_request(
                    self.rfile, self.wfile, headers, httpversion, self.config.body_size_limit
                )
        return flow.Request(
                    client_conn, httpversion, host, port, "http", method, path, headers, content,
                    self.rfile.first_byte_timestamp, utils.timestamp()
               )

    def read_request(self, client_conn):
        self.rfile.reset_timestamps()
        if self.config.transparent_proxy:
            return self.read_request_transparent(client_conn)
        elif self.config.reverse_proxy:
            return self.read_request_reverse(client_conn)
        else:
            return self.read_request_proxy(client_conn)

    def read_headers(self, authenticate=False):
        headers = http.read_headers(self.rfile)
        if headers is None:
            raise ProxyError(400, "Invalid headers")
        if authenticate and self.config.authenticator:
            if self.config.authenticator.authenticate(headers):
                self.config.authenticator.clean(headers)
            else:
                raise ProxyError(
                            407,
                            "Proxy Authentication Required",
                            self.config.authenticator.auth_challenge_headers()
                       )
        return headers

    def send_response(self, response):
        d = response._assemble()
        if not d:
            raise ProxyError(502, "Cannot transmit an incomplete response.")
        self.wfile.write(d)
        self.wfile.flush()

    def send_error(self, code, body, headers):
        try:
            response = http_status.RESPONSES.get(code, "Unknown")
            html_content = '<html><head>\n<title>%d %s</title>\n</head>\n<body>\n%s\n</body>\n</html>'%(code, response, body)
            self.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
            self.wfile.write("Server: %s\r\n"%self.server_version)
            self.wfile.write("Content-type: text/html\r\n")
            self.wfile.write("Content-Length: %d\r\n"%len(html_content))
            for key, value in headers.items():
                self.wfile.write("%s: %s\r\n"%(key, value))
            self.wfile.write("Connection: close\r\n")
            self.wfile.write("\r\n")
            self.wfile.write(html_content)
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
        self.channel = None
        self.apps = AppRegistry()

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_connection(self, request, client_address):
        h = ProxyHandler(self.config, request, client_address, self, self.channel, self.server_version)
        h.handle()
        h.finish()


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

    def start_slave(self, *args):
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


TRANSPARENT_SSL_PORTS = [443, 8443]

def process_proxy_options(parser, options):
    if options.cert:
        options.cert = os.path.expanduser(options.cert)
        if not os.path.exists(options.cert):
            return parser.error("Manually created certificate does not exist: %s"%options.cert)

    cacert = os.path.join(options.confdir, "mitmproxy-ca.pem")
    cacert = os.path.expanduser(cacert)
    if not os.path.exists(cacert):
        certutils.dummy_ca(cacert)
    body_size_limit = utils.parse_size(options.body_size_limit)
    if options.reverse_proxy and options.transparent_proxy:
        return parser.error("Can't set both reverse proxy and transparent proxy.")

    if options.transparent_proxy:
        if not platform.resolver:
            return parser.error("Transparent mode not supported on this platform.")
        trans = dict(
            resolver = platform.resolver(),
            sslports = TRANSPARENT_SSL_PORTS
        )
    else:
        trans = None

    if options.reverse_proxy:
        rp = utils.parse_proxy_spec(options.reverse_proxy)
        if not rp:
            return parser.error("Invalid reverse proxy specification: %s"%options.reverse_proxy)
    else:
        rp = None

    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts) or not os.path.isdir(options.clientcerts):
            return parser.error("Client certificate directory does not exist or is not a directory: %s"%options.clientcerts)

    if (options.auth_nonanonymous or options.auth_singleuser or options.auth_htpasswd):
        if options.auth_singleuser:
            if len(options.auth_singleuser.split(':')) != 2:
                return parser.error("Invalid single-user specification. Please use the format username:password")
            username, password = options.auth_singleuser.split(':')
            password_manager = http_auth.PassManSingleUser(username, password)
        elif options.auth_nonanonymous:
            password_manager = http_auth.PassManNonAnon()
        elif options.auth_htpasswd:
            try:
                password_manager = http_auth.PassManHtpasswd(options.auth_htpasswd)
            except ValueError, v:
                return parser.error(v.message)
        authenticator = http_auth.BasicProxyAuth(password_manager, "mitmproxy")
    else:
        authenticator = http_auth.NullProxyAuth(None)

    return ProxyConfig(
        certfile = options.cert,
        cacert = cacert,
        clientcerts = options.clientcerts,
        body_size_limit = body_size_limit,
        no_upstream_cert = options.no_upstream_cert,
        reverse_proxy = rp,
        transparent_proxy = trans,
        authenticator = authenticator
    )
