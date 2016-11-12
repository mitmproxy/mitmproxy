from mitmproxy import log
from mitmproxy import exceptions
from mitmproxy.proxy import protocol
from mitmproxy.proxy import modes
from mitmproxy.proxy.protocol import http


class RootContext:

    """
    The outermost context provided to the root layer.
    As a consequence, every layer has access to methods and attributes defined here.

    Attributes:
        client_conn:
            The :py:class:`client connection <mitmproxy.connections.ClientConnection>`.
        channel:
            A :py:class:`~mitmproxy.controller.Channel` to communicate with the FlowMaster.
            Provides :py:meth:`.ask() <mitmproxy.controller.Channel.ask>` and
            :py:meth:`.tell() <mitmproxy.controller.Channel.tell>` methods.
        config:
            The :py:class:`proxy server's configuration <mitmproxy.proxy.ProxyConfig>`
    """

    def __init__(self, client_conn, config, channel):
        self.client_conn = client_conn
        self.channel = channel
        self.config = config

    def next_layer(self, top_layer):
        """
        This function determines the next layer in the protocol stack.

        Arguments:
            top_layer: the current innermost layer.

        Returns:
            The next layer
        """
        layer = self._next_layer(top_layer)
        return self.channel.ask("next_layer", layer)

    def _next_layer(self, top_layer):
        try:
            d = top_layer.client_conn.rfile.peek(3)
        except exceptions.TcpException as e:
            raise exceptions.ProtocolException(str(e))
        client_tls = protocol.is_tls_record_magic(d)

        # 1. check for --ignore
        if self.config.check_ignore:
            ignore = self.config.check_ignore(top_layer.server_conn.address)
            if not ignore and client_tls:
                try:
                    client_hello = protocol.TlsClientHello.from_client_conn(self.client_conn)
                except exceptions.TlsProtocolException as e:
                    self.log("Cannot parse Client Hello: %s" % repr(e), "error")
                else:
                    ignore = self.config.check_ignore((client_hello.sni, 443))
            if ignore:
                return protocol.RawTCPLayer(top_layer, ignore=True)

        # 2. Always insert a TLS layer, even if there's neither client nor server tls.
        # An inline script may upgrade from http to https,
        # in which case we need some form of TLS layer.
        if isinstance(top_layer, modes.ReverseProxy):
            return protocol.TlsLayer(
                top_layer,
                client_tls,
                top_layer.server_tls,
                top_layer.server_conn.address.host
            )
        if isinstance(top_layer, protocol.ServerConnectionMixin) or isinstance(top_layer, protocol.UpstreamConnectLayer):
            return protocol.TlsLayer(top_layer, client_tls, client_tls)

        # 3. In Http Proxy mode and Upstream Proxy mode, the next layer is fixed.
        if isinstance(top_layer, protocol.TlsLayer):
            if isinstance(top_layer.ctx, modes.HttpProxy):
                return protocol.Http1Layer(top_layer, http.HTTPMode.regular)
            if isinstance(top_layer.ctx, modes.HttpUpstreamProxy):
                return protocol.Http1Layer(top_layer, http.HTTPMode.upstream)

        # 4. Check for other TLS cases (e.g. after CONNECT).
        if client_tls:
            return protocol.TlsLayer(top_layer, True, True)

        # 4. Check for --tcp
        if self.config.check_tcp(top_layer.server_conn.address):
            return protocol.RawTCPLayer(top_layer)

        # 5. Check for TLS ALPN (HTTP1/HTTP2)
        if isinstance(top_layer, protocol.TlsLayer):
            alpn = top_layer.client_conn.get_alpn_proto_negotiated()
            if alpn == b'h2':
                return protocol.Http2Layer(top_layer, http.HTTPMode.transparent)
            if alpn == b'http/1.1':
                return protocol.Http1Layer(top_layer, http.HTTPMode.transparent)

        # 6. Assume HTTP1 by default
        return protocol.Http1Layer(top_layer, http.HTTPMode.transparent)

    def log(self, msg, level, subs=()):
        """
        Send a log message to the master.
        """
        full_msg = [
            "{}: {}".format(repr(self.client_conn.address), msg)
        ]
        for i in subs:
            full_msg.append("  -> " + i)
        full_msg = "\n".join(full_msg)
        self.channel.tell("log", log.LogEntry(full_msg, level))

    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"
