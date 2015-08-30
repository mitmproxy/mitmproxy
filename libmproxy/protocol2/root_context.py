from __future__ import (absolute_import, print_function, division)

from netlib.http.http1 import HTTP1Protocol
from netlib.http.http2 import HTTP2Protocol

from .rawtcp import RawTcpLayer
from .tls import TlsLayer, is_tls_record_magic
from .http import Http1Layer, Http2Layer
from .layer import ServerConnectionMixin
from ..proxy_modes import HttpProxy, HttpUpstreamProxy, ReverseProxy

class RootContext(object):
    """
    The outmost context provided to the root layer.
    As a consequence, every layer has .client_conn, .channel, .next_layer() and .config.
    """

    def __init__(self, client_conn, config, channel):
        self.client_conn = client_conn  # Client Connection
        self.channel = channel  # provides .ask() method to communicate with FlowMaster
        self.config = config  # Proxy Configuration

    def next_layer(self, top_layer):
        """
        This function determines the next layer in the protocol stack.

        Arguments:
            top_layer: the current top layer.

        Returns:
            The next layer
        """

        # 1. Check for --ignore.
        if self.config.check_ignore(top_layer.server_conn.address):
            return RawTcpLayer(top_layer, logging=False)

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
            return RawTcpLayer(top_layer)

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

    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"
