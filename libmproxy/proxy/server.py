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
        except socket.error as v:
            raise ProxyServerError('Error starting proxy server: ' + repr(v))
        self.channel = None

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(
            self.config,
            conn,
            client_address,
            self,
            self.channel)
        h.handle()
        h.finish()


class ConnectionHandler:
    def __init__(
            self,
            config,
            client_connection,
            client_address,
            server,
            channel):
        self.config = config
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(
            client_connection,
            client_address,
            server)
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.server_conn = None
        """@type: libmproxy.proxy.connection.ServerConnection"""
        self.channel = channel

        self.conntype = "http"

    def handle(self):
        try:
            self.log("clientconnect", "info")

            # Can we already identify the target server and connect to it?
            client_ssl, server_ssl = False, False
            conn_kwargs = dict()
            upstream_info = self.config.mode.get_upstream_server(
                self.client_conn)
            if upstream_info:
                self.set_server_address(upstream_info[2:])
                client_ssl, server_ssl = upstream_info[:2]
                if self.config.check_ignore(self.server_conn.address):
                    self.log(
                        "Ignore host: %s:%s" %
                        self.server_conn.address(),
                        "info")
                    self.conntype = "tcp"
                    conn_kwargs["log"] = False
                    client_ssl, server_ssl = False, False
            else:
                # No upstream info from the metadata: upstream info in the
                # protocol (e.g. HTTP absolute-form)
                pass

            self.channel.ask("clientconnect", self)

            # Check for existing connection: If an inline script already established a
            # connection, do not apply client_ssl or server_ssl.
            if self.server_conn and not self.server_conn.connection:
                self.establish_server_connection()
                if client_ssl or server_ssl:
                    self.establish_ssl(client=client_ssl, server=server_ssl)

                if self.config.check_tcp(self.server_conn.address):
                    self.log(
                        "Generic TCP mode for host: %s:%s" %
                        self.server_conn.address(),
                        "info")
                    self.conntype = "tcp"
                
            elif not self.server_conn and self.config.mode == "sslspoof":
                port = self.config.mode.sslport
                self.set_server_address(("-", port))
                self.establish_ssl(client=True)
                host = self.client_conn.connection.get_servername()
                if host:
                    self.set_server_address((host, port))
                    self.establish_server_connection()
                    self.establish_ssl(server=True, sni=host)

            # Delegate handling to the protocol handler
            protocol_handler(
                self.conntype)(
                self,
                **conn_kwargs).handle_messages()

            self.log("clientdisconnect", "info")
            self.channel.tell("clientdisconnect", self)

        except ProxyError as e:
            protocol_handler(self.conntype)(self, **conn_kwargs).handle_error(e)
        except Exception:
            import traceback
            import sys

            self.log(traceback.format_exc(), "error")
            print >> sys.stderr, traceback.format_exc()
            print >> sys.stderr, "mitmproxy has crashed!"
            print >> sys.stderr, "Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy"
        finally:
            # Make sure that we close the server connection in any case.
            # The client connection is closed by the ProxyServer and does not
            # have be handled here.
            self.del_server_connection()

    def del_server_connection(self):
        """
        Deletes (and closes) an existing server connection.
        """
        if self.server_conn and self.server_conn.connection:
            self.server_conn.finish()
            self.server_conn.close()
            self.log(
                "serverdisconnect", "debug", [
                    "%s:%s" %
                    (self.server_conn.address.host, self.server_conn.address.port)])
            self.channel.tell("serverdisconnect", self)
        self.server_conn = None

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

        self.log(
            "Set new server address: %s:%s" %
            (address.host, address.port), "debug")
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
        self.log(
            "serverconnect", "debug", [
                "%s:%s" %
                self.server_conn.address()[
                    :2]])
        if ask:
            self.channel.ask("serverconnect", self)
        try:
            self.server_conn.connect()
        except tcp.NetLibError as v:
            raise ProxyError(502, v)

    def establish_ssl(self, client=False, server=False, sni=None):
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
                subs.append("with server (sni: %s)" % sni)
            self.log("Establish SSL", "debug", subs)

        if server:
            if not self.server_conn or not self.server_conn.connection:
                raise ProxyError(502, "No server connection.")
            if self.server_conn.ssl_established:
                raise ProxyError(502, "SSL to Server already established.")
            try:
                self.server_conn.establish_ssl(
                    self.config.clientcerts,
                    sni,
                    method=self.config.openssl_method_server,
                    options=self.config.openssl_options_server,
                    verify_options=self.config.openssl_verification_mode_server,
                    ca_path=self.config.openssl_trusted_cadir_server,
                    ca_pemfile=self.config.openssl_trusted_ca_server,
                    cipher_list=self.config.ciphers_server,
                )
                ssl_cert_err = self.server_conn.ssl_verification_error
                if ssl_cert_err is not None:
                    self.log(
                        "SSL verification failed for upstream server at depth %s with error: %s" % 
                            (ssl_cert_err['depth'], ssl_cert_err['errno']),
                        "error")
                    self.log("Ignoring server verification error, continuing with connection", "error")
            except tcp.NetLibError as v:
                e = ProxyError(502, repr(v))
                # Workaround for https://github.com/mitmproxy/mitmproxy/issues/427
                # The upstream server may reject connections without SNI, which means we need to
                # establish SSL with the client first, hope for a SNI (which triggers a reconnect which replaces the
                # ServerConnection object) and see whether that worked.
                if client and "handshake failure" in e.message:
                    self.server_conn.may_require_sni = e
                else:
                    ssl_cert_err = self.server_conn.ssl_verification_error
                    if ssl_cert_err is not None:
                        self.log(
                            "SSL verification failed for upstream server at depth %s with error: %s" % 
                                (ssl_cert_err['depth'], ssl_cert_err['errno']),
                            "error")
                        self.log("Aborting connection attempt", "error")
                    raise e
        if client:
            if self.client_conn.ssl_established:
                raise ProxyError(502, "SSL to Client already established.")
            cert, key, chain_file = self.find_cert()
            try:
                self.client_conn.convert_to_ssl(
                    cert, key,
                    method=self.config.openssl_method_client,
                    options=self.config.openssl_options_client,
                    handle_sni=self.handle_sni,
                    cipher_list=self.config.ciphers_client,
                    dhparams=self.config.certstore.dhparams,
                    chain_file=chain_file
                )
            except tcp.NetLibError as v:
                raise ProxyError(400, repr(v))

            # Workaround for #427 part 2
            if server and hasattr(self.server_conn, "may_require_sni"):
                raise self.server_conn.may_require_sni

    def server_reconnect(self, new_sni=False):
        address = self.server_conn.address
        had_ssl = self.server_conn.ssl_established
        state = self.server_conn.state
        sni = new_sni or self.server_conn.sni
        self.log("(server reconnect follows)", "debug")
        self.del_server_connection()
        self.set_server_address(address)
        self.establish_server_connection()

        for s in state:
            protocol_handler(s[0])(self).handle_server_reconnect(s[1])
        self.server_conn.state = state

        # Receiving new_sni where had_ssl is False is a weird case that happens when the workaround for
        # https://github.com/mitmproxy/mitmproxy/issues/427 is active. In this
        # case, we want to establish SSL as well.
        if had_ssl or new_sni:
            self.establish_ssl(server=True, sni=sni)

    def finish(self):
        self.client_conn.finish()

    def log(self, msg, level, subs=()):
        msg = [
            "%s:%s: %s" %
            (self.client_conn.address.host,
             self.client_conn.address.port,
             msg)]
        for i in subs:
            msg.append("  -> " + i)
        msg = "\n".join(msg)
        self.channel.tell("log", Log(msg, level))

    def find_cert(self):
        host = self.server_conn.address.host
        sans = []
        if self.server_conn.ssl_established and (
                not self.config.no_upstream_cert):
            upstream_cert = self.server_conn.cert
            sans.extend(upstream_cert.altnames)
            if upstream_cert.cn:
                sans.append(host)
                host = upstream_cert.cn.decode("utf8").encode("idna")
        if self.server_conn.sni:
            sans.append(self.server_conn.sni)
        # for ssl spoof mode
        if hasattr(self.client_conn, "sni"):
            sans.append(self.client_conn.sni)

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
            if not sn:
                return
            sni = sn.decode("utf8").encode("idna")
            # for ssl spoof mode
            self.client_conn.sni = sni

            if sni != self.server_conn.sni:
                self.log("SNI received: %s" % sni, "debug")
                # We should only re-establish upstream SSL if one of the following conditions is true:
                #   - We established SSL with the server previously
                #   - We initially wanted to establish SSL with the server,
                #     but the server refused to negotiate without SNI.
                if self.server_conn.ssl_established or hasattr(
                        self.server_conn,
                        "may_require_sni"):
                    # reconnect to upstream server with SNI
                    self.server_reconnect(sni)
                # Now, change client context to reflect changed certificate:
                cert, key, chain_file = self.find_cert()
                new_context = self.client_conn.create_ssl_context(
                    cert, key,
                    method=self.config.openssl_method_client,
                    options=self.config.openssl_options_client,
                    cipher_list=self.config.ciphers_client,
                    dhparams=self.config.certstore.dhparams,
                    chain_file=chain_file
                )
                connection.set_context(new_context)
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except:  # pragma: no cover
            import traceback
            self.log(
                "Error in handle_sni:\r\n" +
                traceback.format_exc(),
                "error")
