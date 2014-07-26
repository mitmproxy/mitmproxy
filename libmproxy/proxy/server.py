from __future__ import absolute_import

import socket
from OpenSSL import SSL

from netlib import tcp
from .primitives import ProxyServerError, Log, ProxyError, ConnectionTypeChange, \
    AddressPriority
from .connection import ClientConnection, ServerConnection
from ..protocol.handle import handle_messages, handle_error
from .. import version


class DummyServer:
    bound = False

    def __init__(self, config):
        self.config = config

    def start_slave(self, *args):
        pass

    def shutdown(self):
        pass


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
        h = ConnectionHandler(self.config, conn, client_address, self, self.channel,
                              self.server_version)
        h.handle()
        h.finish()


class ConnectionHandler:
    def __init__(self, config, client_connection, client_address, server, channel,
                 server_version):
        self.config = config
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(client_connection, client_address, server)
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.server_conn = None
        """@type: libmproxy.proxy.connection.ServerConnection"""
        self.channel, self.server_version = channel, server_version

        self.close = False
        self.conntype = None
        self.sni = None

    def handle(self):
        self.log("clientconnect", "info")
        self.channel.ask("clientconnect", self)

        self.determine_conntype()

        try:
            # Can we already identify the target server and connect to it?
            if self.config.get_upstream_server:
                upstream_info = self.config.get_upstream_server(
                    self.client_conn.connection)
                self.set_server_address(upstream_info[2:], AddressPriority.FROM_SETTINGS)
                client_ssl, server_ssl = upstream_info[:2]
                if client_ssl or server_ssl:
                    self.establish_server_connection()
                    self.establish_ssl(client=client_ssl, server=server_ssl)

            while not self.close:
                try:
                    handle_messages(self.conntype, self)
                except ConnectionTypeChange:
                    self.log("Connection Type Changed: %s" % self.conntype, "info")
                    continue

        except (ProxyError, tcp.NetLibError), e:
            handle_error(self.conntype, self, e)
        except Exception, e:
            import traceback, sys

            self.log(traceback.format_exc(), "error")
            print >> sys.stderr, traceback.format_exc()
            print >> sys.stderr, "mitmproxy has crashed!"
            print >> sys.stderr, "Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy"
            raise e

        self.del_server_connection()
        self.log("clientdisconnect", "info")
        self.channel.tell("clientdisconnect", self)

    def del_server_connection(self):
        """
        Deletes (and closes) an existing server connection.
        """
        if self.server_conn and self.server_conn.connection:
            self.server_conn.finish()
            self.log("serverdisconnect", "debug", ["%s:%s" % (self.server_conn.address.host,
                                                              self.server_conn.address.port)])
            self.channel.tell("serverdisconnect", self)
        self.server_conn = None
        self.sni = None

    def determine_conntype(self):
        #TODO: Add ruleset to select correct protocol depending on mode/target port etc.
        self.conntype = "http"

    def set_server_address(self, address, priority):
        """
        Sets a new server address with the given priority.
        Does not re-establish either connection or SSL handshake.
        """
        address = tcp.Address.wrap(address)

        if self.server_conn:
            if self.server_conn.priority > priority:
                self.log("Attempt to change server address, "
                         "but priority is too low (is: %s, got: %s)" % (
                             self.server_conn.priority, priority), "info")
                return
            if self.server_conn.address == address:
                self.server_conn.priority = priority  # Possibly increase priority
                return

            self.del_server_connection()

        self.log("Set new server address: %s:%s" % (address.host, address.port), "debug")
        self.server_conn = ServerConnection(address, priority)

    def establish_server_connection(self):
        """
        Establishes a new server connection.
        If there is already an existing server connection, the function returns immediately.
        """
        if self.server_conn.connection:
            return
        self.log("serverconnect", "debug", ["%s:%s" % self.server_conn.address()[:2]])
        self.channel.ask("serverconnect", self)
        try:
            self.server_conn.connect()
        except tcp.NetLibError, v:
            raise ProxyError(502, v)

    def establish_ssl(self, client=False, server=False):
        """
        Establishes SSL on the existing connection(s) to the server or the client,
        as specified by the parameters. If the target server is on the pass-through list,
        the conntype attribute will be changed and a ConnTypeChanged exception will be raised.
        """
        # TODO: Implement SSL pass-through handling and change conntype
        passthrough = [
            # "echo.websocket.org",
            # "174.129.224.73"  # echo.websocket.org, transparent mode
        ]
        if self.server_conn.address.host in passthrough or self.sni in passthrough:
            self.conntype = "tcp"
            raise ConnectionTypeChange

        # Logging
        if client or server:
            subs = []
            if client:
                subs.append("with client")
            if server:
                subs.append("with server (sni: %s)" % self.sni)
            self.log("Establish SSL", "debug", subs)

        if server:
            if self.server_conn.ssl_established:
                raise ProxyError(502, "SSL to Server already established.")
            self.establish_server_connection()  # make sure there is a server connection.
            self.server_conn.establish_ssl(self.config.clientcerts, self.sni)
        if client:
            if self.client_conn.ssl_established:
                raise ProxyError(502, "SSL to Client already established.")
            cert, key = self.find_cert()
            self.client_conn.convert_to_ssl(
                cert, key,
                handle_sni=self.handle_sni,
                cipher_list=self.config.ciphers,
                dhparams=self.config.certstore.dhparams,
                ca_file=self.config.ca_file
            )

    def server_reconnect(self, no_ssl=False):
        address = self.server_conn.address
        had_ssl = self.server_conn.ssl_established
        priority = self.server_conn.priority
        sni = self.sni
        self.log("(server reconnect follows)", "debug")
        self.del_server_connection()
        self.set_server_address(address, priority)
        self.establish_server_connection()
        if had_ssl and not no_ssl:
            self.sni = sni
            self.establish_ssl(server=True)

    def finish(self):
        self.client_conn.finish()

    def log(self, msg, level, subs=()):
        msg = [
            "%s:%s: %s" % (self.client_conn.address.host, self.client_conn.address.port, msg)
        ]
        for i in subs:
            msg.append("  -> " + i)
        msg = "\n".join(msg)
        self.channel.tell("log", Log(msg, level))

    def find_cert(self):
        if self.config.certforward and self.server_conn.ssl_established:
            return self.server_conn.cert, self.config.certstore.gen_pkey(self.server_conn.cert)
        else:
            host = self.server_conn.address.host
            sans = []
            if not self.config.no_upstream_cert and self.server_conn.ssl_established:
                upstream_cert = self.server_conn.cert
                if upstream_cert.cn:
                    host = upstream_cert.cn.decode("utf8").encode("idna")
                sans = upstream_cert.altnames
            elif self.config.no_upstream_cert and self.sni:
                sans = [self.sni]

            ret = self.config.certstore.get_cert(host, sans)
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
                self.log("SNI received: %s" % self.sni, "debug")
                self.server_reconnect()  # reconnect to upstream server with SNI
                # Now, change client context to reflect changed certificate:
                cert, key = self.find_cert()
                new_context = self.client_conn._create_ssl_context(
                    cert, key,
                    method=SSL.TLSv1_METHOD,
                    cipher_list=self.config.ciphers,
                    dhparams=self.config.certstore.dhparams,
                    ca_file=self.config.ca_file
                )
                connection.set_context(new_context)
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except Exception:  # pragma: no cover
            import traceback
            self.log("Error in handle_sni:\r\n" + traceback.format_exc(), "error")
