from __future__ import (absolute_import, print_function, division)

from .rawtcp import RawTcpLayer
from .tls import TlsLayer
from .http import Http1Layer, Http2Layer, HttpLayer

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

        d = top_layer.client_conn.rfile.peek(3)

        # TODO: Handle ignore and tcp passthrough

        # TLS ClientHello magic, see http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
        is_tls_client_hello = (
            len(d) == 3 and
            d[0] == '\x16' and
            d[1] == '\x03' and
            d[2] in ('\x00', '\x01', '\x02', '\x03')
        )

        # TODO: build is_http2_magic check here, maybe this is an easy way to detect h2c

        if not d:
            return

        if is_tls_client_hello:
            return TlsLayer(top_layer, True, True)
        elif isinstance(top_layer, TlsLayer):
            if top_layer.client_conn.get_alpn_proto_negotiated() == 'h2':
                return Http2Layer(top_layer, 'regular')  # TODO: regular correct here?
            else:
                return Http1Layer(top_layer, 'regular')  # TODO: regular correct here?
        elif isinstance(top_layer, TlsLayer) and isinstance(top_layer.ctx, Http1Layer):
            return Http1Layer(top_layer, "transparent")
        else:
            return RawTcpLayer(top_layer)


    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"
