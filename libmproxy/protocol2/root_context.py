from __future__ import (absolute_import, print_function, division)

from .rawtcp import RawTcpLayer
from .tls import TlsLayer


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

        if not d:
            return

        if is_tls_client_hello:
            layer = TlsLayer(top_layer, True, True)
        else:
            layer = RawTcpLayer(top_layer)
        return layer

    @property
    def layers(self):
        return []

    def __repr__(self):
        return "RootContext"
