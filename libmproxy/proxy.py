import os, socket, time, threading
from OpenSSL import SSL
from netlib import tcp, http, certutils, http_auth, stateobject
import utils, version, platform, controller


TRANSPARENT_SSL_PORTS = [443, 8443]


class ProxyError(Exception):
    def __init__(self, code, msg, headers=None):
        self.code, self.msg, self.headers = code, msg, headers

    def __str__(self):
        return "ProxyError(%s, %s)" % (self.code, self.msg)

class Log:
    def __init__(self, msg):
        self.msg = msg


class ProxyConfig:
    def __init__(self, certfile=None, cacert=None, clientcerts=None, no_upstream_cert=False, body_size_limit=None,
                 reverse_proxy=None, forward_proxy=None, transparent_proxy=None, authenticator=None):
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


class ClientConnection(tcp.BaseHandler, stateobject.SimpleStateObject):
    def __init__(self, client_connection, address, server):
        if client_connection:  # Eventually, this object is restored from state
            tcp.BaseHandler.__init__(self, client_connection, address, server)
        else:
            self.address = None
            self.clientcert = None

        self.timestamp_start = utils.timestamp()
        self.timestamp_end = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        timestamp_start=float,
        timestamp_end=float,
        timestamp_ssl_setup=float,
        address=tcp.Address,
        clientcert=certutils.SSLCert
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None, None)
        f._load_state(state)
        return f

    def convert_to_ssl(self, *args, **kwargs):
        tcp.BaseHandler.convert_to_ssl(self, *args, **kwargs)
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        tcp.BaseHandler.finish(self)
        self.timestamp_end = utils.timestamp()


class ServerConnection(tcp.TCPClient, stateobject.SimpleStateObject):
    def __init__(self, address):
        tcp.TCPClient.__init__(self, address)

        self.peername = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        peername=tuple,
        timestamp_start=float,
        timestamp_end=float,
        timestamp_tcp_setup=float,
        timestamp_ssl_setup=float,
        address=tcp.Address,
        source_address=tcp.Address,
        cert=certutils.SSLCert
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None)
        f._load_state(state)
        return f

    def connect(self):
        self.timestamp_start = utils.timestamp()
        tcp.TCPClient.connect(self)
        self.peername = self.connection.getpeername()
        self.timestamp_tcp_setup = utils.timestamp()

    def send(self, message):
        self.wfile.write(message)
        self.wfile.flush()

    def establish_ssl(self, clientcerts, sni):
        clientcert = None
        if clientcerts:
            path = os.path.join(clientcerts, self.address.host.encode("idna")) + ".pem"
            if os.path.exists(path):
                clientcert = path
        try:
            self.convert_to_ssl(cert=clientcert, sni=sni)
            self.timestamp_ssl_setup = utils.timestamp()
        except tcp.NetLibError, v:
            raise ProxyError(400, str(v))

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = utils.timestamp()


"""
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
            httpversion, code, msg, headers, content = http.read_response(
                server.rfile, r.method, self.config.body_size_limit
            )
            response = flow.Response(
                self.flow.request, httpversion, code, msg, headers, content, server.cert, 
                server.rfile.first_byte_timestamp
            )
            self.channel.ask("response", response)
        except (ProxyError, http.HttpError, tcp.NetLibError), v:
            err = flow.Error(self.flow.request, str(v))
            self.channel.ask("error", err)
"""


import protocol

class ConnectionHandler:
    def __init__(self, config, client_connection, client_address, server, channel, server_version):
        self.config = config
        self.client_conn = ClientConnection(client_connection, client_address, server)
        self.server_conn = None
        self.channel, self.server_version = channel, server_version

        self.close = False
        self.conntype = None
        self.sni = None

        self.mode = "regular"
        if self.config.reverse_proxy:
            self.mode = "reverse"
        if self.config.transparent_proxy:
            self.mode = "transparent"

    def del_server_connection(self):
        if self.server_conn and self.server_conn.connection:
            self.server_conn.finish()
            self.log("serverdisconnect", ["%s:%s" % (self.server_conn.address.host, self.server_conn.address.port)])
            self.channel.tell("serverdisconnect", self)
        self.server_conn = None
        self.sni = None

    def handle(self):
        self.log("clientconnect")
        self.channel.ask("clientconnect", self)

        self.determine_conntype()

        try:
            try:
                # Can we already identify the target server and connect to it?
                server_address = None
                if self.config.forward_proxy:
                    server_address = self.config.forward_proxy[1:]
                else:
                    if self.config.reverse_proxy:
                        server_address = self.config.reverse_proxy[1:]
                    elif self.config.transparent_proxy:
                        server_address = self.config.transparent_proxy["resolver"].original_addr(
                            self.client_conn.connection)
                        if not server_address:
                            raise ProxyError(502, "Transparent mode failure: could not resolve original destination.")
                        self.log("transparent to %s:%s" % server_address)

                if server_address:
                    self.establish_server_connection(server_address)
                    self._handle_ssl()

                while not self.close:
                    try:
                        protocol.handle_messages(self.conntype, self)
                    except protocol.ConnectionTypeChange:
                        continue

            # FIXME: Do we want to persist errors?
            except (ProxyError, tcp.NetLibError), e:
                protocol.handle_error(self.conntype, self, e)
        except Exception, e:
            self.log(e.__class__)
            import traceback
            self.log(traceback.format_exc())
            self.log(str(e))

        self.del_server_connection()
        self.log("clientdisconnect")
        self.channel.tell("clientdisconnect", self)

    def _handle_ssl(self):
        """
        Check if we can already identify SSL connections.
        """
        if self.config.transparent_proxy:
            client_ssl = server_ssl = (self.server_conn.address.port in self.config.transparent_proxy["sslports"])
        elif self.config.reverse_proxy:
            client_ssl = server_ssl = (self.config.reverse_proxy[0] == "https")
            # TODO: Make protocol generic (as with transparent proxies)
            # TODO: Add SSL-terminating capatbility (SSL -> mitmproxy -> plain and vice versa)
        self.establish_ssl(client=client_ssl, server=server_ssl)

    def finish(self):
        self.client_conn.finish()

    def determine_conntype(self):
        #TODO: Add ruleset to select correct protocol depending on mode/target port etc.
        self.conntype = "http"

    def establish_server_connection(self, address):
        """
        Establishes a new server connection to the given server
        If there is already an existing server connection, it will be killed.
        """
        self.del_server_connection()
        self.server_conn = ServerConnection(address)
        try:
            self.server_conn.connect()
        except tcp.NetLibError, v:
            raise ProxyError(502, v)
        self.log("serverconnect", ["%s:%s" % address])
        self.channel.tell("serverconnect", self)

    def establish_ssl(self, client=False, server=False):
        """
        Establishes SSL on the existing connection(s) to the server or the client,
        as specified by the parameters. If the target server is on the pass-through list,
        the conntype attribute will be changed and no the SSL connection won't be wrapped.
        A protocol handler must raise a ConnTypeChanged exception if it detects that this is happening
        """
        # TODO: Implement SSL pass-through handling and change conntype
        if self.server_conn.address.host == "news.ycombinator.com":
            self.conntype = "tcp"

        if server:
            if self.server_conn.ssl_established:
                raise ProxyError(502, "SSL to Server already established.")
            self.server_conn.establish_ssl(self.config.clientcerts, self.sni)
        if client:
            if self.client_conn.ssl_established:
                raise ProxyError(502, "SSL to Client already established.")
            dummycert = self.find_cert()
            self.client_conn.convert_to_ssl(dummycert, self.config.certfile or self.config.cacert,
                                            handle_sni=self.handle_sni)

    def server_reconnect(self, no_ssl=False):
        had_ssl, sni = self.server_conn.ssl_established, self.sni
        self.log("server reconnect (ssl: %s, sni: %s)" % (had_ssl, sni))
        self.establish_server_connection(self.server_conn.address)
        if had_ssl and not no_ssl:
            self.sni = sni
            self.establish_ssl(server=True)

    def log(self, msg, subs=()):
        msg = [
            "%s:%s: %s" % (self.client_conn.address.host, self.client_conn.address.port, msg)
        ]
        for i in subs:
            msg.append("  -> " + i)
        msg = "\n".join(msg)
        self.channel.tell("log", Log(msg))

    def find_cert(self):
        if self.config.certfile:
            with open(self.config.certfile, "rb") as f:
                return certutils.SSLCert.from_pem(f.read())
        else:
            host = self.server_conn.address.host
            sans = []
            if not self.config.no_upstream_cert or not self.server_conn.ssl_established:
                upstream_cert = self.server_conn.cert
                if upstream_cert.cn:
                    host = upstream_cert.cn.decode("utf8").encode("idna")
                sans = upstream_cert.altnames

            ret = self.config.certstore.get_cert(host, sans, self.config.cacert)
            if not ret:
                raise ProxyError(502, "Unable to generate dummy cert.")
            return ret

    def handle_sni(self, connection):
        """
        This callback gets called during the SSL handshake with the client.
        The client has just sent the Sever Name Indication (SNI). We now connect upstream to
        figure out which certificate needs to be served.
        """
        try:
            sn = connection.get_servername()
            if sn and sn != self.sni:
                self.sni = sn.decode("utf8").encode("idna")
                self.server_reconnect()  # reconnect to upstream server with SNI
                # Now, change client context to reflect changed certificate:
                new_context = SSL.Context(SSL.TLSv1_METHOD)
                new_context.use_privatekey_file(self.config.certfile or self.config.cacert)
                dummycert = self.find_cert()
                new_context.use_certificate(dummycert.x509)
                connection.set_context(new_context)
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except Exception, e: # pragma: no cover
            pass


class ProxyServerError(Exception): pass


class ProxyServer(tcp.TCPServer):
    allow_reuse_address = True
    bound = True

    def __init__(self, config, port, host='', server_version=version.NAMEVERSION):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config = config
        self.server_version = server_version
        try:
            tcp.TCPServer.__init__(self, (host, port))
        except socket.error, v:
            raise ProxyServerError('Error starting proxy server: ' + v.strerror)
        self.channel = None

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(self.config, conn, client_address, self, self.channel, self.server_version)
        h.handle()
        h.finish()


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
        type=str, dest="cert", default=None,
        help="User-created SSL certificate file."
    )
    group.add_argument(
        "--client-certs", action="store",
        type=str, dest="clientcerts", default=None,
        help="Client certificate directory."
    )


def process_proxy_options(parser, options):
    if options.cert:
        options.cert = os.path.expanduser(options.cert)
        if not os.path.exists(options.cert):
            return parser.error("Manually created certificate does not exist: %s" % options.cert)

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
            resolver=platform.resolver(),
            sslports=TRANSPARENT_SSL_PORTS
        )
    else:
        trans = None

    if options.reverse_proxy:
        rp = utils.parse_proxy_spec(options.reverse_proxy)
        if not rp:
            return parser.error("Invalid reverse proxy specification: %s" % options.reverse_proxy)
    else:
        rp = None

    if options.forward_proxy:
        fp = utils.parse_proxy_spec(options.forward_proxy)
        if not fp:
            return parser.error("Invalid forward proxy specification: %s" % options.forward_proxy)
    else:
        fp = None

    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts) or not os.path.isdir(options.clientcerts):
            return parser.error(
                "Client certificate directory does not exist or is not a directory: %s" % options.clientcerts
            )

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
        certfile=options.cert,
        cacert=cacert,
        clientcerts=options.clientcerts,
        body_size_limit=body_size_limit,
        no_upstream_cert=options.no_upstream_cert,
        reverse_proxy=rp,
        forward_proxy=fp,
        transparent_proxy=trans,
        authenticator=authenticator
    )
