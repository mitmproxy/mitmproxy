from __future__ import (absolute_import, print_function, division)
import string

from libmproxy.protocol2.layer import Kill
from .rawtcp import RawTcpLayer
from .tls import TlsLayer
from .http import Http1Layer, Http2Layer, HttpLayer

from netlib.http.http2 import HTTP2Protocol

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
        :param top_layer: the current top layer
        :return: The next layer.
        """

        # TODO: Handle ignore and tcp passthrough

        # TLS ClientHello magic, works for SSLv3, TLSv1.0, TLSv1.1, TLSv1.2
        # http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
        d = top_layer.client_conn.rfile.peek(3)
        is_tls_client_hello = (
            len(d) == 3 and
            d[0] == '\x16' and
            d[1] == '\x03' and
            d[2] in ('\x00', '\x01', '\x02', '\x03')
        )

        d = top_layer.client_conn.rfile.peek(3)
        is_ascii = (
            len(d) == 3 and
            all(x in string.ascii_letters for x in d) # better be safe here and don't expect uppercase...
        )

        d = top_layer.client_conn.rfile.peek(len(HTTP2Protocol.CLIENT_CONNECTION_PREFACE))
        is_http2_magic = (d == HTTP2Protocol.CLIENT_CONNECTION_PREFACE)

        is_alpn_h2_negotiated = (
            isinstance(top_layer, TlsLayer) and
            top_layer.client_conn.get_alpn_proto_negotiated() == HTTP2Protocol.ALPN_PROTO_H2
        )

        if is_tls_client_hello:
            return TlsLayer(top_layer, True, True)
        elif is_alpn_h2_negotiated or is_http2_magic:
            return Http2Layer(top_layer, 'transparent')
        elif is_ascii:
            return Http1Layer(top_layer, 'transparent')
        else:
            return RawTcpLayer(top_layer)

    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"
