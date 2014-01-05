import sys, os, string, socket, time
import shutil, tempfile, threading
import SocketServer
from OpenSSL import SSL
from netlib import odict, tcp, http, wsgi, certutils, http_status, http_auth
import utils, flow, version, platform, controller, protocol


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
    def __init__(self, certfile = None, cacert = None, clientcerts = None, no_upstream_cert=False, body_size_limit = None, reverse_proxy=None, forward_proxy=None, transparent_proxy=None, authenticator=None):
        self.certfile = certfile
        self.cacert = cacert
        self.clientcerts = clientcerts
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.reverse_proxy = reverse_proxy
        self.forward_proxy = forward_proxy
        self.transparent_proxy = transparent_proxy
        self.authenticator = authenticator
        self.certstore = certutils.CertStore()


class ServerConnection(tcp.TCPClient):
    def __init__(self, config, host, port, sni):
        tcp.TCPClient.__init__(self, host, port)
        self.config = config
        self.sni = sni
        self.tcp_setup_timestamp = None
        self.ssl_setup_timestamp = None

    def connect(self):
        tcp.TCPClient.connect(self)
        self.tcp_setup_timestamp = time.time()

    def establish_ssl(self):
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
        print "deprecated"
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
    def __init__(self, handler, cert, key):
        self.handler = handler
        self.cert, self.key = cert, key

    def __call__(self, connection):
        try:
            sn = connection.get_servername()
            if sn:
                self.handler.sni = sn.decode("utf8").encode("idna")
                self.handler.establish_server_connection()
                self.handler.handle_ssl()
                new_context = SSL.Context(SSL.TLSv1_METHOD)
                new_context.use_privatekey_file(self.key)
                new_context.use_certificate(self.cert.x509)
                connection.set_context(new_context)
                # FIXME: How does that work?
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except Exception, e: # pragma: no cover
            pass


class ConnectionHandler:
    def __init__(self, config, client_connection, client_address, server, channel, server_version):
        self.config = config
        self.client_address, self.client_conn = client_address, tcp.BaseHandler(client_connection)
        self.server_address, self.server_conn = None, None
        self.channel, self.server_version = channel, server_version

        self.conntype = None
        self.sni = None

        self.mode = "regular"
        if self.config.reverse_proxy:
            self.mode = "reverse"
        if self.config.transparent_proxy:
            self.mode = "transparent"

    def del_server_connection(self):
        if self.server_conn:
            self.server_conn.terminate()
        self.server_conn = None

    def handle(self):
        cc = flow.ClientConnect(self.client_address)
        self.log(cc, "connect")
        self.channel.ask(cc)

        # Can we already identify the target server and connect to it?
        if self.config.forward_proxy:
            self.server_address = self.config.forward_proxy
        else:
            if self.config.reverse_proxy:
                self.server_address = self.config.reverse_proxy
            elif self.config.transparent_proxy:
                self.server_address = self.config.transparent_proxy["resolver"].original_addr(self.connection)
                if not self.server_address:
                    raise ProxyError(502, "Transparent mode failure: could not resolve original destination.")
                self.log(cc, "transparent to %s:%s"%self.server_address)

        if self.server_address:
            self.establish_server_connection()
            self.handle_ssl()

        self.determine_conntype(self.mode)

        while not cc.close:
            protocol.handle_messages(self.conntype, self)

        cc.close = True
        self.del_server_connection()

        cd = flow.ClientDisconnect(cc)
        self.log(
            cc, "disconnect",
            [
                "handled %s requests"%cc.requestcount]
        )
        self.channel.tell(cd)

    def determine_conntype(self, mode):
        #TODO: Add ruleset to select correct protocol depending on mode/target port etc.
        self.conntype = "http"

    def establish_server_connection(self):
        """
        Establishes a new server connection to self.server_address.
        If there is already an existing server connection, it will be killed.
        """
        self.del_server_connection()
        self.server_conn = ServerConnection(self.config, *self.server_address, self.sni)

    def handle_ssl(self):
        if self.config.transparent_proxy:
            client_ssl, server_ssl = (self.server_address[1] in self.config.transparent_proxy["sslports"])
        elif self.config.reverse_proxy:
            client_ssl, server_ssl = self.config.reverse_proxy[0] == "https"
            # FIXME: Make protocol generic (as with transparent proxies)
            # FIXME: Add SSL-terminating capatbility (SSL -> mitmproxy -> plain and vice versa)
        else:
            client_ssl, server_ssl = True  # In regular mode, this function will only be called on HTTP CONNECT

        # TODO: Implement SSL pass-through handling and change conntype

        if server_ssl and not self.server_conn.ssl_established:
            self.server_conn.establish_ssl()
        if client_ssl and not self.client_conn.ssl_established:
            dummycert = self.find_cert(self.client_conn, *self.server_address)
            sni = HandleSNI(
                self, dummycert, self.config.certfile or self.config.cacert
            )

    def log(self, msg, subs=()):
        msg = [
            "%s:%s: "%self.client_address + msg
        ]
        for i in subs:
            msg.append("  -> "+i)
        msg = "\n".join(msg)
        l = Log(msg)
        self.channel.tell(l)

    def find_cert(self, cc, host, port, sni=None):
        if self.config.certfile:
            with open(self.config.certfile, "rb") as f:
                return certutils.SSLCert.from_pem(f.read())
        else:
            sans = []
            if not self.config.no_upstream_cert:
                conn = self.get_server_connection(cc, "https", host, port, sni)
                sans = conn.cert.altnames
                if conn.cert.cn:
                    host = conn.cert.cn.decode("utf8").encode("idna")
            ret = self.config.certstore.get_cert(host, sans, self.config.cacert)
            if not ret:
                raise ProxyError(502, "Unable to generate dummy cert.")
            return ret


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

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(self.config, conn, client_address, self, self.channel, self.server_version)
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

    if options.forward_proxy:
        fp = utils.parse_proxy_spec(options.forward_proxy)
        if not fp:
            return parser.error("Invalid forward proxy specification: %s"%options.forward_proxy)
    else:
        fp = None

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
        forward_proxy = fp,
        transparent_proxy = trans,
        authenticator = authenticator
    )
