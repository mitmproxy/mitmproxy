from __future__ import (absolute_import, print_function, division)

from netlib.http.http1 import HTTP1Protocol
from netlib.http.http2 import HTTP2Protocol

from ..protocol import (
    RawTCPLayer, TlsLayer, Http1Layer, Http2Layer, is_tls_record_magic, ServerConnectionMixin
)
from .modes import HttpProxy, HttpUpstreamProxy, ReverseProxy


class RootContext(object):
    """
    The outermost context provided to the root layer.
    As a consequence, every layer has access to methods and attributes defined here.

    Attributes:
        client_conn:
            The :py:class:`client connection <libmproxy.models.ClientConnection>`.
        channel:
            A :py:class:`~libmproxy.controller.Channel` to communicate with the FlowMaster.
            Provides :py:meth:`.ask() <libmproxy.controller.Channel.ask>` and
            :py:meth:`.tell() <libmproxy.controller.Channel.tell>` methods.
        config:
            The :py:class:`proxy server's configuration <libmproxy.proxy.ProxyConfig>`
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
        # 1. Check for --ignore.
        if self.config.check_ignore(top_layer.server_conn.address):
            return RawTCPLayer(top_layer, logging=False)

        d = top_layer.client_conn.rfile.peek(3)
        client_tls = is_tls_record_magic(d)

        # 2. Always insert a TLS layer, even if there's neither client nor server tls.
        # An inline script may upgrade from http to https,
        # in which case we need some form of TLS layer.
        if isinstance(top_layer, ReverseProxy):
            return TlsLayer(top_layer, client_tls, top_layer.server_tls)
        if isinstance(top_layer, ServerConnectionMixin):
            return TlsLayer(top_layer, client_tls, client_tls)

        # 3. In Http Proxy mode and Upstream Proxy mode, the next layer is fixed.
        if isinstance(top_layer, TlsLayer):
            if isinstance(top_layer.ctx, HttpProxy):
                return Http1Layer(top_layer, "regular")
            if isinstance(top_layer.ctx, HttpUpstreamProxy):
                return Http1Layer(top_layer, "upstream")

        # 4. Check for other TLS cases (e.g. after CONNECT).
        if client_tls:
            return TlsLayer(top_layer, True, True)

        # 4. Check for --tcp
        if self.config.check_tcp(top_layer.server_conn.address):
            return RawTCPLayer(top_layer)

        # 5. Check for TLS ALPN (HTTP1/HTTP2)
        if isinstance(top_layer, TlsLayer):
            alpn = top_layer.client_conn.get_alpn_proto_negotiated()
            if alpn == HTTP2Protocol.ALPN_PROTO_H2:
                return Http2Layer(top_layer, 'transparent')
            if alpn == HTTP1Protocol.ALPN_PROTO_HTTP1:
                return Http1Layer(top_layer, 'transparent')

        # 6. Assume HTTP1 by default
        return Http1Layer(top_layer, 'transparent')

        # In a future version, we want to implement TCP passthrough as the last fallback,
        # but we don't have the UI part ready for that.
        #
        # d = top_layer.client_conn.rfile.peek(3)
        # is_ascii = (
        #     len(d) == 3 and
        #     # better be safe here and don't expect uppercase...
        #     all(x in string.ascii_letters for x in d)
        # )
        # # TODO: This could block if there are not enough bytes available?
        # d = top_layer.client_conn.rfile.peek(len(HTTP2Protocol.CLIENT_CONNECTION_PREFACE))
        # is_http2_magic = (d == HTTP2Protocol.CLIENT_CONNECTION_PREFACE)

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
        self.channel.tell("log", Log(full_msg, level))

    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"


class Log(object):
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level
