from __future__ import absolute_import

import socket
from OpenSSL import SSL

from netlib import tcp
from .primitives import ProxyServerError, Log, ProxyError
from .connection import ClientConnection, ServerConnection
from ..protocol.handle import protocol_handler
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

    def __init__(self, config):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config = config
        try:
            tcp.TCPServer.__init__(self, (config.host, config.port))
        except socket.error, v:
            raise ProxyServerError('Error starting proxy server: ' + repr(v))
        self.channel = None

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(self.config, conn, client_address, self, self.channel)
        h.handle()
        h.finish()


class ConnectionHandler:
    def __init__(self, config, client_connection, client_address, server, channel):
        self.config = config
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(client_connection, client_address, server)
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.server_conn = None
        """@type: libmproxy.proxy.connection.ServerConnection"""
        self.channel = channel

        self.conntype = "http"
        self.sni = None

    def handle(self):
        try:
            self.log("clientconnect", "info")

            # Can we already identify the target server and connect to it?
            client_ssl, server_ssl = False, False
            conn_kwargs = dict()
            upstream_info = self.config.mode.get_upstream_server(self.client_conn)
            if upstream_info:
                self.set_server_address(upstream_info[2:])
                client_ssl, server_ssl = upstream_info[:2]
                if self.config.check_ignore(self.server_conn.address):
                    self.log("Ignore host: %s:%s" % self.server_conn.address(), "info")
                    self.conntype = "tcp"
                    conn_kwargs["log"] = False
                    client_ssl, server_ssl = False, False
            else:
                pass  # No upstream info from the metadata: upstream info in the protocol (e.g. HTTP absolute-form)

            self.channel.ask("clientconnect", self)

            # Check for existing connection: If an inline script already established a
            # connection, do not apply client_ssl or server_ssl.
            if self.server_conn and not self.server_conn.connection:
                self.establish_server_connection()
                if client_ssl or server_ssl:
                    self.establish_ssl(client=client_ssl, server=server_ssl)

                if self.config.check_tcp(self.server_conn.address):
                    self.log("Generic TCP mode for host: %s:%s" % self.server_conn.address(), "info")
                    self.conntype = "tcp"

            # Delegate handling to the protocol handler
            protocol_handler(self.conntype)(self, **conn_kwargs).handle_messages()

            self.log("clientdisconnect", "info")
            self.channel.tell("clientdisconnect", self)

        except ProxyError as e:
            protocol_handler(self.conntype)(self, **conn_kwargs).handle_error(e)
        except Exception:
            import traceback, sys

            self.log(traceback.format_exc(), "error")
            print >> sys.stderr, traceback.format_exc()
            print >> sys.stderr, "mitmproxy has crashed!"
            print >> sys.stderr, "Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy"
        finally:
            # Make sure that we close the server connection in any case.
            # The client connection is closed by the ProxyServer and does not have be handled here.
            self.del_server_connection()

    def del_server_connection(self):
        """
        Deletes (and closes) an existing server connection.
        """
        if self.server_conn and self.server_conn.connection:
            self.server_conn.finish()
            self.server_conn.close()
            self.log("serverdisconnect", "debug", ["%s:%s" % (self.server_conn.address.host,
                                                              self.server_conn.address.port)])
            self.channel.tell("serverdisconnect", self)
        self.server_conn = None
        self.sni = None

    def set_server_address(self, address):
        """
        Sets a new server address with the given priority.
        Does not re-establish either connection or SSL handshake.
        """
        address = tcp.Address.wrap(address)

        # Don't reconnect to the same destination.
        if self.server_conn and self.server_conn.address == address:
            return

        if self.server_conn:
            self.del_server_connection()

        self.log("Set new server address: %s:%s" % (address.host, address.port), "debug")
        self.server_conn = ServerConnection(address)

    def establish_server_connection(self, ask=True):
        """
        Establishes a new server connection.
        If there is already an existing server connection, the function returns immediately.

        By default, this function ".ask"s the proxy master. This is deadly if this function is already called from the
        master (e.g. via change_server), because this navigates us in a simple deadlock (the master is single-threaded).
        In these scenarios, ask=False can be passed to suppress the call to the master.
        """
        if self.server_conn.connection:
            return
        self.log("serverconnect", "debug", ["%s:%s" % self.server_conn.address()[:2]])
        if ask:
            self.channel.ask("serverconnect", self)
        try:
            self.server_conn.connect()
        except tcp.NetLibError, v:
            raise ProxyError(502, v)

    def establish_ssl(self, client=False, server=False):
        """
        Establishes SSL on the existing connection(s) to the server or the client,
        as specified by the parameters.
        """

        # Logging
        if client or server:
            subs = []
            if client:
                subs.append("with client")
            if server:
                subs.append("with server (sni: %s)" % self.sni)
            self.log("Establish SSL", "debug", subs)

        if server:
            if not self.server_conn or not self.server_conn.connection:
                raise ProxyError(502, "No server connection.")
            if self.server_conn.ssl_established:
                raise ProxyError(502, "SSL to Server already established.")
            try:
                self.server_conn.establish_ssl(self.config.clientcerts, self.sni)
            except tcp.NetLibError as v:
                raise ProxyError(502, repr(v))
        if client:
            if self.client_conn.ssl_established:
                raise ProxyError(502, "SSL to Client already established.")
            cert, key, chain_file = self.find_cert()
            try:
                self.client_conn.convert_to_ssl(
                    cert, key,
                    handle_sni=self.handle_sni,
                    cipher_list=self.config.ciphers,
                    dhparams=self.config.certstore.dhparams,
                    chain_file=chain_file
                )
            except tcp.NetLibError as v:
                raise ProxyError(400, repr(v))

    def server_reconnect(self):
        address = self.server_conn.address
        had_ssl = self.server_conn.ssl_established
        state = self.server_conn.state
        sni = self.sni
        self.log("(server reconnect follows)", "debug")
        self.del_server_connection()
        self.set_server_address(address)
        self.establish_server_connection()

        for s in state:
            protocol_handler(s[0])(self).handle_server_reconnect(s[1])
        self.server_conn.state = state

        if had_ssl:
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
            return self.server_conn.cert, self.config.certstore.gen_pkey(self.server_conn.cert), None
        else:
            host = self.server_conn.address.host
            sans = []
            if self.server_conn.ssl_established and (not self.config.no_upstream_cert):
                upstream_cert = self.server_conn.cert
                if upstream_cert.cn:
                    host = upstream_cert.cn.decode("utf8").encode("idna")
                sans = upstream_cert.altnames
            elif self.sni:
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
                cert, key, chain_file = self.find_cert()
                new_context = self.client_conn._create_ssl_context(
                    cert, key,
                    method=SSL.TLSv1_METHOD,
                    cipher_list=self.config.ciphers,
                    dhparams=self.config.certstore.dhparams,
                    chain_file=chain_file
                )
                connection.set_context(new_context)
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except:  # pragma: no cover
            import traceback
            self.log("Error in handle_sni:\r\n" + traceback.format_exc(), "error")
