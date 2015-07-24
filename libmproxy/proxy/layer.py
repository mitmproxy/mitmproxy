from __future__ import (absolute_import, print_function, division, unicode_literals)
import Queue
import threading
import traceback
from libmproxy.protocol.tcp import TCPHandler
from libmproxy.proxy.connection import ServerConnection
from netlib import tcp
from .primitives import Socks5ProxyMode, ProxyError, Log
from .message import Connect, Reconnect, ChangeServer

"""
mitmproxy protocol architecture

In mitmproxy, protocols are implemented as a set of layers, which are composed on top each other.
For example, the following scenarios depict possible scenarios (lowest layer first):

Transparent HTTP proxy, no SSL:
    TransparentModeLayer
    HttpLayer

Regular proxy, CONNECT request with WebSockets over SSL:
    RegularModeLayer
    HttpLayer
    SslLayer
    WebsocketLayer (or TcpLayer)

Automated protocol detection by peeking into the buffer:
    TransparentModeLayer
    AutoLayer
    SslLayer
    AutoLayer
    Http2Layer

Communication between layers is done as follows:
    - lower layers provide context information to higher layers
    - higher layers can "yield" commands to lower layers,
      which are propagated until they reach a suitable layer.

Further goals:
  - Connections should always be peekable to make automatic protocol detection work.
  - Upstream connections should be established as late as possible;
    inline scripts shall have a chance to handle everything locally.
"""


class ProxyError2(Exception):
    def __init__(self, message, cause=None):
        super(ProxyError2, self).__init__(message)
        self.cause = cause


class RootContext(object):
    """
    The outmost context provided to the root layer.
    As a consequence, every layer has .client_conn, .channel and .config.
    """

    def __init__(self, client_conn, config, channel):
        self.client_conn = client_conn  # Client Connection
        self.channel = channel  # provides .ask() method to communicate with FlowMaster
        self.config = config  # Proxy Configuration

    def __getattr__(self, name):
        """
        Accessing a nonexisting attribute does not throw an error but returns None instead.
        """
        return None


class _LayerCodeCompletion(object):
    """
    Dummy class that provides type hinting in PyCharm, which simplifies development a lot.
    """

    def __init__(self):
        if True:
            return
        self.config = None
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = None
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.channel = None
        """@type: libmproxy.controller.Channel"""


class Layer(_LayerCodeCompletion):
    def __init__(self, ctx):
        """
        Args:
            ctx: The (read-only) higher layer.
        """
        super(Layer, self).__init__()
        self.ctx = ctx

    def __call__(self):
        """
        Logic of the layer.
        Raises:
            ProxyError2 in case of protocol exceptions.
        """
        raise NotImplementedError

    def __getattr__(self, name):
        """
        Attributes not present on the current layer may exist on a higher layer.
        """
        return getattr(self.ctx, name)

    def log(self, msg, level, subs=()):
        full_msg = [
            "%s:%s: %s" %
            (self.client_conn.address.host,
             self.client_conn.address.port,
             msg)]
        for i in subs:
            full_msg.append("  -> " + i)
        full_msg = "\n".join(full_msg)
        self.channel.tell("log", Log(full_msg, level))


class _ServerConnectionMixin(object):
    """
    Mixin that provides a layer with the capabilities to manage a server connection.
    """

    def __init__(self):
        self.server_address = None
        self.server_conn = None

    def _handle_server_message(self, message):
        if message == Reconnect:
            self._disconnect()
            self._connect()
            return True
        elif message == Connect:
            self._connect()
            return True
        elif message == ChangeServer:
            raise NotImplementedError
        return False

    def _disconnect(self):
        """
        Deletes (and closes) an existing server connection.
        """
        self.log("serverdisconnect", "debug", [repr(self.server_address)])
        self.server_conn.finish()
        self.server_conn.close()
        # self.channel.tell("serverdisconnect", self)
        self.server_conn = None

    def _connect(self):
        self.log("serverconnect", "debug", [repr(self.server_address)])
        self.server_conn = ServerConnection(self.server_address)
        try:
            self.server_conn.connect()
        except tcp.NetLibError as e:
            raise ProxyError2("Server connection to '%s' failed: %s" % (self.server_address, e), e)

    def _set_address(self, address):
        a = tcp.Address.wrap(address)
        self.log("Set new server address: " + repr(a), "debug")
        self.server_address = address


class Socks5IncomingLayer(Layer, _ServerConnectionMixin):
    def __call__(self):
        try:
            s5mode = Socks5ProxyMode(self.config.ssl_ports)
            address = s5mode.get_upstream_server(self.client_conn)[2:]
        except ProxyError as e:
            # TODO: Unmonkeypatch
            raise ProxyError2(str(e), e)

        self._set_address(address)

        if address[1] == 443:
            layer = SslLayer(self, True, True)
        else:
            layer = TcpLayer(self)
        for message in layer():
            if not self._handle_server_message(message):
                yield message


class TcpLayer(Layer):
    def __call__(self):
        yield Connect()
        tcp_handler = TCPHandler(self)
        tcp_handler.handle_messages()

    def establish_server_connection(self):
        pass
        # FIXME: Remove method, currently just here to mock TCPHandler's call to it.


class ReconnectRequest(object):
    def __init__(self):
        self.done = threading.Event()


class SslLayer(Layer):
    def __init__(self, ctx, client_ssl, server_ssl):
        super(SslLayer, self).__init__(ctx)
        self._client_ssl = client_ssl
        self._server_ssl = server_ssl
        self._connected = False
        self._sni_from_handshake = None
        self._sni_from_server_change = None

    def __call__(self):
        """
        The strategy for establishing SSL is as follows:
            First, we determine whether we need the server cert to establish ssl with the client.
            If so, we first connect to the server and then to the client.
            If not, we only connect to the client and do the server_ssl lazily on a Connect message.

        An additional complexity is that establish ssl with the server may require a SNI value from the client.
        In an ideal world, we'd do the following:
            1. Start the SSL handshake with the client
            2. Check if the client sends a SNI.
            3. Pause the client handshake, establish SSL with the server.
            4. Finish the client handshake with the certificate from the server.
        There's just one issue: We cannot get a callback from OpenSSL if the client doesn't send a SNI. :(
        Thus, we resort to the following workaround when establishing SSL with the server:
            1. Try to establish SSL with the server without SNI. If this fails, we ignore it.
            2. Establish SSL with client.
                - If there's a SNI callback, reconnect to the server with SNI.
                - If not and the server connect failed, raise the original exception.
        Further notes:
            - OpenSSL 1.0.2 introduces a callback that would help here:
              https://www.openssl.org/docs/ssl/SSL_CTX_set_cert_cb.html
            - The original mitmproxy issue is https://github.com/mitmproxy/mitmproxy/issues/427
        """
        client_ssl_requires_server_cert = (
            self._client_ssl and self._server_ssl and not self.config.no_upstream_cert
        )
        lazy_server_ssl = (
            self._server_ssl and not client_ssl_requires_server_cert
        )

        if client_ssl_requires_server_cert:
            for m in self._establish_ssl_with_client_and_server():
                yield m
        elif self.client_ssl:
            self._establish_ssl_with_client()

        layer = TcpLayer(self)
        for message in layer():
            if message != Connect or not self._connected:
                yield message
            if message == Connect:
                if lazy_server_ssl:
                    self._establish_ssl_with_server()
            if message == ChangeServer and message.depth == 1:
                self.server_ssl = message.server_ssl
                self._sni_from_server_change = message.sni
            if message == Reconnect or message == ChangeServer:
                if self.server_ssl:
                    self._establish_ssl_with_server()

    @property
    def sni(self):
        if self._sni_from_server_change is False:
            return None
        else:
            return self._sni_from_server_change or self._sni_from_handshake

    def _establish_ssl_with_client_and_server(self):
        """
        This function deals with the problem that the server may require a SNI value from the client.
        """

        # First, try to connect to the server.
        yield Connect()
        self._connected = True
        server_err = None
        try:
            self._establish_ssl_with_server()
        except ProxyError2 as e:
            server_err = e

        # The part below is a bit ugly as we cannot yield from the handle_sni callback.
        # The workaround is to do that in a separate thread and yield from the main thread.

        # client_ssl_queue may contain the following elements
        # - True, if ssl was successfully established
        # - An Exception thrown by self._establish_ssl_with_client()
        # - A threading.Event, which singnifies a request for a reconnect from the sni callback
        self.__client_ssl_queue = Queue.Queue()

        def establish_client_ssl():
            try:
                self._establish_ssl_with_client()
                self.__client_ssl_queue.put(True)
            except Exception as client_err:
                self.__client_ssl_queue.put(client_err)

        threading.Thread(target=establish_client_ssl, name="ClientSSLThread").start()
        e = self.__client_ssl_queue.get()
        if isinstance(e, ReconnectRequest):
            yield Reconnect()
            self._establish_ssl_with_server()
            e.done.set()
            e = self.__client_ssl_queue.get()
        if e is not True:
            raise ProxyError2("Error when establish client SSL: " + repr(e), e)
        self.__client_ssl_queue = None

        if server_err and not self._sni_from_handshake:
            raise server_err

    def handle_sni(self, connection):
        """
        This callback gets called during the SSL handshake with the client.
        The client has just sent the Sever Name Indication (SNI).
        """
        try:
            sn = connection.get_servername()
            if not sn:
                return
            sni = sn.decode("utf8").encode("idna")

            if sni != self.sni:
                self._sni_from_handshake = sni

                # Perform reconnect
                if self.server_ssl:
                    reconnect = ReconnectRequest()
                    self.__client_ssl_queue.put()
                    reconnect.done.wait()

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
            self.log("Error in handle_sni:\r\n" + traceback.format_exc(), "error")

    def _establish_ssl_with_client(self):
        self.log("Establish SSL with client", "debug")
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
        except tcp.NetLibError as e:
            raise ProxyError2(repr(e), e)

    def _establish_ssl_with_server(self):
        self.log("Establish SSL with server", "debug")
        try:
            self.server_conn.establish_ssl(
                self.config.clientcerts,
                self.sni,
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
        except tcp.NetLibInvalidCertificateError as e:
            ssl_cert_err = self.server_conn.ssl_verification_error
            self.log(
                "SSL verification failed for upstream server at depth %s with error: %s" %
                (ssl_cert_err['depth'], ssl_cert_err['errno']),
                "error")
            self.log("Aborting connection attempt", "error")
            raise ProxyError2(repr(e), e)
        except Exception as e:
            raise ProxyError2(repr(e), e)

    def find_cert(self):
        host = self.server_conn.address.host
        sans = []
        # Incorporate upstream certificate
        if self.server_conn.ssl_established and (not self.config.no_upstream_cert):
            upstream_cert = self.server_conn.cert
            sans.extend(upstream_cert.altnames)
            if upstream_cert.cn:
                sans.append(host)
                host = upstream_cert.cn.decode("utf8").encode("idna")
        # Also add SNI values.
        if self._sni_from_handshake:
            sans.append(self._sni_from_handshake)
        if self._sni_from_server_change:
            sans.append(self._sni_from_server_change)

        return self.config.certstore.get_cert(host, sans)
