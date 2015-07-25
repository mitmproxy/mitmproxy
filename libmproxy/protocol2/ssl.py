from __future__ import (absolute_import, print_function, division, unicode_literals)
import Queue
import threading
import traceback
from netlib import tcp

from ..proxy import ProxyError2
from .layer import Layer
from .messages import Connect, Reconnect, ChangeServer
from .auto import AutoLayer


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

        layer = AutoLayer(self)
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